// =============================================================================
// Alert Webhook Receiver — receives alerts from Alertmanager
// and forwards them to Telegram and email.
// Usage: node alert-webhook.js
// =============================================================================

const http = require("http");
const https = require("https");

const PORT = 5001;
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN || "";
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID || "";
const ADMIN_EMAIL = process.env.ADMIN_EMAIL || "";

function sendTelegram(text) {
  if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) return;

  const data = JSON.stringify({
    chat_id: TELEGRAM_CHAT_ID,
    text: text,
    parse_mode: "Markdown",
  });

  const options = {
    hostname: "api.telegram.org",
    port: 443,
    path: `/bot${TELEGRAM_BOT_TOKEN}/sendMessage`,
    method: "POST",
    headers: { "Content-Type": "application/json" },
  };

  const req = https.request(options, (res) => {
    if (res.statusCode !== 200) {
      console.error("Telegram API error:", res.statusCode);
    }
  });

  req.write(data);
  req.end();
}

function sendEmail(text) {
  if (!ADMIN_EMAIL) return;
  console.log("[EMAIL] Would send to", ADMIN_EMAIL, ":", text);
}

function formatAlert(alert) {
  const severity = alert.status === "firing" ? "🔴" : "🟢";
  const summary = alert.annotations?.summary || alert.alertname;
  const description = alert.annotations?.description || "";

  return `${severity} *${alert.alertname}*\n${summary}\n${description}\nStatus: \`${alert.status}\``;
}

const server = http.createServer((req, res) => {
  if (req.method === "POST" && req.url === "/webhook") {
    let body = "";

    req.on("data", (chunk) => {
      body += chunk.toString();
    });

    req.on("end", () => {
      try {
        const alerts = JSON.parse(body);
        const messages = alerts.alerts.map((alert) => formatAlert(alert));
        const message = messages.join("\n\n---\n\n");

        console.log("Alert received:", message);
        sendTelegram(message);
        sendEmail(message);

        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ status: "ok" }));
      } catch (err) {
        console.error("Error processing alert:", err);
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ status: "error", message: err.message }));
      }
    });
  } else {
    res.writeHead(404);
    res.end();
  }
});

server.listen(PORT, () => {
  console.log(`Alert webhook receiver listening on port ${PORT}`);
});
