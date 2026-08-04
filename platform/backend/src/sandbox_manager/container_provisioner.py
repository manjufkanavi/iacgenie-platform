"""Stub container_provisioner."""


class SandboxProvisionError(Exception):
    pass


class ContainerNotFoundError(Exception):
    pass


class ContainerProvisioner:
    def __init__(self, *args, **kwargs):
        pass

    def create_container(self, *args, **kwargs):
        pass

    def destroy_container(self, *args, **kwargs):
        pass
