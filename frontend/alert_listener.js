const ALERT_COLORS = {
  LOW: '#2d6cdf',
  MEDIUM: '#f0a202',
  HIGH: '#d7263d'
};

function renderAlertBanner(alert) {
  const container = document.getElementById('alert-banner-container');
  if (!container) return;

  const banner = document.createElement('div');
  banner.className = 'alert-banner';
  banner.style.borderLeft = `6px solid ${ALERT_COLORS[alert.severity] || '#2d6cdf'}`;
  banner.innerHTML = `
    <strong>${alert.type}</strong>
    <span>${alert.summary}</span>
    <small>Score: ${Number(alert.event_score).toFixed(2)} | Confidence: ${Number(alert.confidence_score).toFixed(2)}</small>
  `;
  container.prepend(banner);

  while (container.children.length > 5) {
    container.removeChild(container.lastChild);
  }
}

export function startAlertsSocket() {
  const ws = new WebSocket(`${window.location.origin.replace('http', 'ws')}/ws/alerts`);

  ws.onmessage = (event) => {
    const alert = JSON.parse(event.data);
    renderAlertBanner(alert);

    if (window.dispatchEvent) {
      window.dispatchEvent(new CustomEvent('market-alert', { detail: alert }));
    }
  };

  ws.onerror = () => {
    console.warn('alerts websocket disconnected');
  };

  return ws;
}
