// داشبورد سمت کلاینت - ارتباط با API

const API_BASE = window.location.origin.replace(':8080', ':5001'); // یا IP هاست

let currentSymbol = 'BTCIRT';
let currentTimeframe = '1h';

// دریافت وضعیت سلامت
async function fetchHealth() {
    try {
        const res = await fetch(`${API_BASE}/health`);
        const data = await res.json();
        document.getElementById('ws-status').innerHTML = '🟢 آنلاین';
        document.getElementById('ws-status').className = 'online';
        document.getElementById('last-update').innerText = data.timestamp ? 
            new Date(data.timestamp).toLocaleTimeString('fa-IR') : '---';
        return true;
    } catch(e) {
        document.getElementById('ws-status').innerHTML = '🔴 خاموش';
        document.getElementById('ws-status').className = 'offline';
        return false;
    }
}

// دریافت قیمت‌های لحظه‌ای
async function fetchPrices() {
    try {
        const res = await fetch(`${API_BASE}/market/prices`);
        const data = await res.json();
        
        if (data.prices && data.prices.length) {
            updateSymbolsGrid(data.prices);
        }
    } catch(e) {
        console.log('Market API not ready yet');
    }
}

// بروزرسانی گرید نمادها
function updateSymbolsGrid(prices) {
    const grid = document.getElementById('symbols-grid');
    if (!grid) return;
    
    grid.innerHTML = prices.map(p => {
        const changeClass = p.change_24h >= 0 ? 'positive' : 'negative';
        const changeSymbol = p.change_24h >= 0 ? '▲' : '▼';
        
        return `
            <div class="card" onclick="selectSymbol('${p.symbol}')">
                <div class="symbol">${p.symbol}</div>
                <div class="price">${formatNumber(p.price)}</div>
                <div class="change ${changeClass}">${changeSymbol} ${Math.abs(p.change_24h).toFixed(2)}%</div>
                <div class="small">خرید: ${formatNumber(p.best_buy)}</div>
                <div class="small">فروش: ${formatNumber(p.best_sell)}</div>
            </div>
        `;
    }).join('');
}

// دریافت پیش‌بینی برای یک نماد
async function fetchPrediction(symbol, timeframe) {
    try {
        const res = await fetch(`${API_BASE}/predict/${symbol}?timeframe=${timeframe}`);
        if (res.ok) {
            const data = await res.json();
            updatePredictionCard(data);
            return data;
        }
    } catch(e) {
        console.log('Prediction API not ready yet');
    }
    return null;
}

// بروزرسانی کارت پیش‌بینی
function updatePredictionCard(pred) {
    const card = document.getElementById('prediction-card');
    if (!card) return;
    
    const changeClass = pred.predicted_change_pct >= 0 ? 'positive' : 'negative';
    const direction = pred.predicted_change_pct >= 0 ? '🟢 صعودی' : '🔴 نزولی';
    
    card.innerHTML = `
        <h3>🔮 پیش‌بینی ${pred.symbol}</h3>
        <div class="price">${formatNumber(pred.predicted_price)}</div>
        <div class="change ${changeClass}">${pred.predicted_change_pct.toFixed(2)}% ${direction}</div>
        <div class="small">قیمت فعلی: ${formatNumber(pred.current_price)}</div>
        <div class="small">⏱️ ${new Date(pred.timestamp).toLocaleTimeString('fa-IR')}</div>
    `;
}

// دریافت لاگ‌ها
async function fetchLogs() {
    try {
        const res = await fetch(`${API_BASE}/logs?lines=20`);
        const data = await res.json();
        const panel = document.getElementById('log-panel');
        
        if (panel && data.logs && data.logs.length) {
            panel.innerHTML = data.logs.map(l => `<div class="log-line">${escapeHtml(l)}</div>`).join('');
        }
    } catch(e) {}
}

// دریافت متریک‌های سیستم
async function fetchSystemMetrics() {
    try {
        const res = await fetch(`${API_BASE}/system/info`);
        if (res.ok) {
            const data = await res.json();
            document.getElementById('ram').innerHTML = `${data.memory_used_mb?.toFixed(0) || '?'} MB / ${data.memory_percent?.toFixed(0) || '?'}%`;
        }
    } catch(e) {
        document.getElementById('ram').innerHTML = '---';
    }
}

// انتخاب نماد (وقتی کاربر کلیک می‌کند)
async function selectSymbol(symbol) {
    currentSymbol = symbol;
    await fetchPrediction(currentSymbol, currentTimeframe);
}

// فرمت کردن اعداد
function formatNumber(num) {
    if (!num || num === 0) return '0';
    if (num > 1000000) return (num / 1000000).toFixed(2) + 'M';
    if (num > 1000) return (num / 1000).toFixed(2) + 'K';
    return num.toFixed(2);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// پاک‌سازی لاگ
async function clearLogs() {
    await fetch(`${API_BASE}/logs`, { method: 'DELETE' });
    fetchLogs();
}

// تابع بروزرسانی همه
async function refreshAll() {
    await fetchHealth();
    await fetchPrices();
    await fetchLogs();
    await fetchSystemMetrics();
    await fetchPrediction(currentSymbol, currentTimeframe);
}

// اجرای اولیه و تناوبی
document.addEventListener('DOMContentLoaded', () => {
    refreshAll();
    
    setInterval(refreshAll, 15000); // هر 15 ثانیه
    
    // اگر دکمه پاک‌سازی لاگ هست
    const clearBtn = document.getElementById('clear-logs-btn');
    if (clearBtn) {
        clearBtn.onclick = clearLogs;
    }
});

// expose برای onclick در HTML
window.selectSymbol = selectSymbol;
