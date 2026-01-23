class AdminDashboard {
    constructor() {
        this.init();
    }

    async init() {
        await this.fetchMetrics();
        setInterval(() => this.fetchMetrics(), 5000);
    }

    async fetchMetrics() {
        try {
            const response = await fetch('/api/v1/admin/resources');
            if (response.ok) {
                const data = await response.json();
                this.updateUI(data);
            }
        } catch (e) {
            console.error('Failed to fetch metrics', e);
        }
    }

    updateUI(data) {
        this.updateGauge('cpu', data.cpu_percent);
        this.updateGauge('mem', data.memory_percent);
        this.updateGauge('disk', data.disk_free_percent);
        
        const throttleEl = document.getElementById('throttleValue');
        const levels = ['NORMAL', 'LIGHT', 'HEAVY', 'PAUSE'];
        throttleEl.textContent = levels[data.throttle_level] || data.throttle_level;
        throttleEl.style.color = data.throttle_level > 0 ? 'var(--color-danger)' : 'var(--color-success)';
    }

    updateGauge(type, value) {
        const valueEl = document.getElementById(`${type}Value`);
        const barEl = document.querySelector(`#${type}Bar > div`);
        
        if (valueEl) valueEl.textContent = `${value.toFixed(1)}%`;
        if (barEl) {
            barEl.style.width = `${Math.min(value, 100)}%`;
            if (value > 85) barEl.style.background = 'var(--color-danger)';
            else if (value > 70) barEl.style.background = 'var(--color-warning)';
            else barEl.style.background = 'var(--color-success)';
        }
    }
}

async function triggerScraper(source) {
    const resEl = document.getElementById('actionResult');
    resEl.textContent = 'Triggering...';
    try {
        const response = await fetch(`/api/v1/admin/scraper/trigger/${source}`, { method: 'POST' });
        const data = await response.json();
        resEl.textContent = `Scraper triggered: ${data.task_id}`;
    } catch (e) {
        resEl.textContent = `Error: ${e.message}`;
    }
}

async function triggerCleanup() {
    const resEl = document.getElementById('actionResult');
    resEl.textContent = 'Triggering cleanup...';
    try {
        const response = await fetch(`/api/v1/admin/cleanup/trigger`, { method: 'POST' });
        const data = await response.json();
        resEl.textContent = `Cleanup triggered: ${data.task_id}`;
    } catch (e) {
        resEl.textContent = `Error: ${e.message}`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new AdminDashboard();
});
