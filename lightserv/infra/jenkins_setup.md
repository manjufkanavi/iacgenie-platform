# Jenkins CI/CD Setup and Deployment Guide

## 1. Overview & Architecture

This document outlines the architecture, deployment strategy, and configuration for the Jenkins CI/CD instance deployed within the IacGenie infrastructure. 

The Jenkins instance is designed with **Infrastructure as Code (IaC)** and **Configuration as Code (CasC)** principles at its core. By eliminating manual UI-based configuration, we ensure the CI/CD pipeline is fully reproducible, version-controlled, and secure from the moment it boots.

### Core Technologies:
- **Platform:** Jenkins LTS (Dockerized)
- **Deployment:** Docker Compose
- **Configuration:** Jenkins Configuration as Code (JCasC)
- **Ingress:** Cloudflared (Zero Trust Tunnels)
- **Security:** Project Matrix Authorization Strategy & BCrypt Hashing

---

## 2. Infrastructure Environment (VM Details)

The Jenkins container operates on a dedicated Virtual Machine within the internal network.

* **Hostname:** `newvm` (internal), `vm.iacgenie.com`
* **Internal IP:** `192.168.0.118`
* **Operating System:** Linux (Debian/Ubuntu-based)
* **Access Protocol:** SSH (ED25519 Keys)

### SSH Configuration & Access
Access to the VM is secured via public key cryptography. SSH access should be configured in your local `~/.ssh/config` to streamline connectivity:

```ssh-config
Host newvm
    HostName 192.168.0.118
    User root # or deployment user
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no
```

> [!CAUTION]
> The ED25519 private key is required for access. Ensure this key is heavily guarded and rotated according to security policies.

---

## 3. Container Deployment (Docker Compose)

Jenkins is deployed via `docker-compose-newvm.yml`. The container runs in a custom network stack and exposes its internal application port directly to the host loopback adapter, ensuring traffic is strictly managed by the ingress layer.

### Networking & Volumes
* **Port Mapping:** `127.0.0.1:8085 -> 8080/tcp` (Ensures Jenkins is inaccessible directly from the network; traffic must flow through Cloudflared).
* **Persistence:** The `jenkins_data` volume is mounted to `/var/jenkins_home` to persist plugins, workspaces, and job history across container restarts.
* **Workspace:** The host's `workspace` directory is mounted into the container to allow Jenkins to manipulate local infrastructure code.

### Base Image & Modifications
The container builds upon `jenkins/jenkins:lts-jdk17`. During the `docker compose build` phase:
1. Core CLI tools (Node.js, Python 3, pip, venv) are installed for CI build capabilities.
2. The Docker CLI is installed to enable Docker-in-Docker (DinD) or Docker-out-of-Docker (DooD) pipelines.
3. Our custom `jenkins.config.yml` (JCasC) and `startup.sh` scripts are injected into the `/usr/share/jenkins/ref/` directory.

---

## 4. Bootstrapping & Plugin Management

We bypass the standard Jenkins UI Setup Wizard (`-Djenkins.install.runSetupWizard=false`) to ensure a zero-touch deployment. 

The custom `startup.sh` script executes as the container `ENTRYPOINT` prior to launching the Jetty server. It is responsible for:
1. **Directory Validation:** Running `mkdir -p /var/jenkins_home/plugins` to ensure the target persistence layer exists.
2. **Plugin Installation:** Dynamically downloading and installing essential plugins via `jenkins-plugin-cli`:
   - `configuration-as-code` (Required for JCasC)
   - `matrix-auth` (Required for granular user security)
3. **Configuration Injection:** Copying the injected `.jpi` files and `jenkins.config.yml` from the ephemeral `ref` directory into the persistent `/var/jenkins_home` volume.

> [!TIP]
> If Jenkins boots into an unsecured state, it usually indicates a failure in the `startup.sh` execution. Verify that the script successfully downloaded and copied `configuration-as-code.jpi` and `matrix-auth.jpi` to `/var/jenkins_home/plugins/`.

---

## 5. Configuration as Code (JCasC)

The entire Jenkins configuration (Security, Execution Modes, User Management) is defined declaratively in `jenkins.config.yml`.

### Environment Variables
JCasC relies on the following environment variable declared in the `docker-compose` file to locate its configuration schema:
```yaml
CASC_JENKINS_CONFIG: /var/jenkins_home/jenkins.yml
```
*(Note: Older or incorrect documentation sometimes references `JENKINS_CASC_FILE`, which is invalid and will cause JCasC to silently ignore your configuration).*

### Security & Authentication Strategy
Jenkins is secured using the `local` security realm and the `projectMatrix` authorization strategy.

```yaml
jenkins:
  authorizationStrategy:
    projectMatrix:
      entries:
        - user:
            name: "admin"
            permissions:
              - Overall/Administer
  securityRealm:
    local:
      allowsSignup: false
      users:
        - id: "admin"
          password: "${JENKINS_ADMIN_PASSWORD}"
```

> [!WARNING]
> **Strict Schema Adherence:** JCasC is incredibly strict regarding its YAML schema. 
> 1. `authorizationStrategy` and `securityRealm` **must** reside at the root of the `jenkins:` block (not nested inside arbitrary keys like `globalSecurityConfig`).
> 2. The credential attribute for a local user must be defined as `password` (even if you supply a `#jbcrypt:` hash string). Using invalid attributes like `passwordHash` will cause a `ConfigurationAsCodeBootFailure` exception and abort the security setup.
> 3. Invalid properties (such as misnaming `fingerprints` to `fingerprinterConfig` under the `unclassified:` block) will cause JCasC to immediately crash the configuration process.

---

## 6. Ingress & Routing (Cloudflare)

Jenkins is exposed securely to the internet without opening firewall ports by utilizing **Cloudflared Zero Trust Tunnels**.

* **Public URL:** `https://jenkins.iacgenie.com`
* **Daemon:** The `cloudflared` agent runs natively on the VM (`192.168.0.118`) as a systemd service.
* **Routing:** Cloudflare terminates SSL/TLS at the edge network and routes incoming requests via the secure tunnel directly to `http://127.0.0.1:8085` on the VM loopback adapter.

> [!NOTE]
> **502 Bad Gateway:** If you receive a 502 error at `jenkins.iacgenie.com`, it means the tunnel is active, but the Jenkins container has not fully bound to port `8085`. This commonly occurs for 2-3 minutes during container restart while `jenkins-plugin-cli` downloads dependencies.

---

## 7. Operational Usage & Updates

### Deploying Configuration Changes
To safely apply modifications to the infrastructure or JCasC configuration:

1. **Modify Code:** Update `docker-compose-newvm.yml` or `jenkins.config.yml` in your local `terragenius` repository.
2. **Sync Files:** Push changes to the VM using `rsync`:
   ```bash
   rsync -avz iacgenie/docker/jenkins/ newvm:~/docker/iacgenie/docker/jenkins/
   rsync -avz iacgenie/docker-compose-newvm.yml newvm:~/docker/iacgenie/docker-compose-newvm.yml
   ```
3. **Rebuild & Restart:** Execute the Docker cycle over SSH:
   ```bash
   ssh newvm "cd ~/docker/iacgenie && \
   docker compose -f docker-compose-newvm.yml stop jenkins && \
   rm -f ~/docker/iacgenie/jenkins_data/config.xml ~/docker/iacgenie/jenkins_data/jenkins.model.JenkinsIdentityConfiguration.xml && \
   docker compose -f docker-compose-newvm.yml build jenkins && \
   docker compose -f docker-compose-newvm.yml up -d jenkins"
   ```
*(Note: Explicitly removing `config.xml` is critical to ensure legacy configurations do not override JCasC settings during boot).*

### Log Monitoring
To track deployment progress or debug plugin installations:
```bash
ssh newvm "docker logs -f iacgenie-jenkins"
```
Filter specifically for JCasC boot exceptions:
```bash
ssh newvm "docker logs iacgenie-jenkins 2>&1 | grep -i casc"
```
