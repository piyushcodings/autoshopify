// Enhanced navigation
function showSection(section) {
    // Hide ALL sections first
    document.querySelectorAll('[id$="Section"]').forEach(el => {
        if (el.id !== 'advancedSection' && el.id !== 'bulkSection') {
            el.classList.add('hidden');
        }
    });
    
    // Show selected section
    const selected = document.getElementById(section + 'Section');
    if (selected) {
        selected.classList.remove('hidden');
        document.querySelector('.flex-1.overflow-y-auto').scrollTop = 0;
    }
    
    // Update title
    const titles = {
        dashboard: 'Dashboard',
        checker: 'CC Checker',
        mass: 'Mass Check',
        logs: 'System Logs',
        sites: 'Site Management',
        proxies: 'Proxy Management',
        users: 'User Management',
        analytics: 'Analytics',
        performance: 'Performance',
        settings: 'Settings',
        advanced: 'Advanced Settings',
        bulk: 'Bulk Operations',
        api: 'API Management',
        security: 'Security'
    };
    document.getElementById('pageTitle').textContent = titles[section] || section;
    document.getElementById('pageDescription').textContent = 'Real-time overview';
    
    // Update sidebar
    document.querySelectorAll('.sidebar-item').forEach(item => item.classList.remove('active'));
    event.currentTarget.classList.add('active');
    
    // Load data
    if (section === 'sites') loadSites();
    if (section === 'proxies') loadProxies();
    if (section === 'users') loadUsers();
    if (section === 'logs') refreshLogs();
    if (section === 'analytics') initAnalyticsCharts();
}

// Enhanced CC Checker with loading states
let checkRunning = false;
let checkController = null;

document.getElementById('checkerForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    if (checkRunning) return;
    
    const cc = document.getElementById('cc').value;
    const site = document.getElementById('site').value;
    const proxy = document.getElementById('proxy').value;
    const checkBtn = document.getElementById('checkBtn');
    const stopBtn = document.getElementById('stopCheckBtn');
    const loadingStatus = document.getElementById('loadingStatus');
    
    checkRunning = true;
    checkBtn.classList.add('hidden');
    stopBtn.classList.remove('hidden');
    loadingStatus.classList.remove('hidden');
    document.getElementById('resultSection').classList.add('hidden');
    
    // Reset step icons
    for (let i = 1; i <= 5; i++) {
        const icon = document.getElementById('step' + i + 'Icon');
        if (icon) {
            icon.className = 'fas fa-circle text-gray-300 text-xs';
        }
    }
    
    let url = `/process?key=md-tech&cc=${encodeURIComponent(cc)}&site=${encodeURIComponent(site)}`;
    if (proxy) url += `&proxy=${encodeURIComponent(proxy)}`;
    
    try {
        checkController = new AbortController();
        const timeoutId = setTimeout(() => checkController.abort(), 120000);
        
        // Update steps
        setTimeout(() => {
            const icon1 = document.getElementById('step1Icon');
            if (icon1) icon1.className = 'fas fa-check-circle text-green-500 text-xs';
            document.getElementById('loadingSubtitle').textContent = 'Detecting and solving captcha...';
        }, 1000);
        
        setTimeout(() => {
            const icon2 = document.getElementById('step2Icon');
            if (icon2) icon2.className = 'fas fa-check-circle text-green-500 text-xs';
            document.getElementById('loadingSubtitle').textContent = 'Creating checkout session...';
        }, 3000);
        
        setTimeout(() => {
            const icon3 = document.getElementById('step3Icon');
            if (icon3) icon3.className = 'fas fa-check-circle text-green-500 text-xs';
            document.getElementById('loadingSubtitle').textContent = 'Tokenizing card...';
        }, 5000);
        
        setTimeout(() => {
            const icon4 = document.getElementById('step4Icon');
            if (icon4) icon4.className = 'fas fa-check-circle text-green-500 text-xs';
            document.getElementById('loadingSubtitle').textContent = 'Submitting for completion...';
        }, 7000);
        
        const response = await fetch(url, { signal: checkController.signal });
        clearTimeout(timeoutId);
        const data = await response.json();
        
        // Mark all steps complete
        for (let i = 1; i <= 5; i++) {
            const icon = document.getElementById('step' + i + 'Icon');
            if (icon) icon.className = 'fas fa-check-circle text-green-500 text-xs';
        }
        
        document.getElementById('loadingTitle').textContent = 'Complete!';
        document.getElementById('loadingSubtitle').textContent = 'Results ready';
        
        setTimeout(() => {
            loadingStatus.classList.add('hidden');
            checkBtn.classList.remove('hidden');
            stopBtn.classList.add('hidden');
            checkRunning = false;
            
            const resultsGrid = document.getElementById('resultsGrid');
            resultsGrid.innerHTML = `
                <div class="bg-gray-50 p-4 rounded-lg">
                    <p class="text-sm text-gray-600">Amount</p>
                    <p class="text-lg font-bold">${data.amount || '-'}</p>
                </div>
                <div class="bg-gray-50 p-4 rounded-lg">
                    <p class="text-sm text-gray-600">Status</p>
                    <p class="text-lg font-bold ${data.status === 'Approved' ? 'text-green-600' : 'text-red-600'}">${data.status || '-'}</p>
                </div>
                <div class="bg-gray-50 p-4 rounded-lg">
                    <p class="text-sm text-gray-600">Response</p>
                    <p class="text-lg">${data.response || '-'}</p>
                </div>
                <div class="bg-gray-50 p-4 rounded-lg">
                    <p class="text-sm text-gray-600">Site</p>
                    <p class="text-lg font-bold">${data.site || '-'}</p>
                </div>
                <div class="bg-gray-50 p-4 rounded-lg col-span-2">
                    <p class="text-sm text-gray-600">Captcha Solved</p>
                    <p class="text-lg font-bold">${data.captcha_solved ? '✅ Yes' : '❌ No'}</p>
                </div>
                ${data.captcha_token ? `
                <div class="bg-blue-50 p-4 rounded-lg col-span-2">
                    <p class="text-sm text-blue-600">✅ Captcha Token Generated</p>
                    <p class="text-xs font-mono break-all mt-2">${data.captcha_token.substring(0, 100)}...</p>
                </div>
                ` : ''}
            `;
            
            document.getElementById('resultSection').classList.remove('hidden');
        }, 1500);
        
    } catch (error) {
        if (error.name === 'AbortError') {
            alert('Check stopped by user');
        } else {
            alert('Error: ' + error.message);
        }
        stopCheck();
    }
});

function stopCheck() {
    if (checkController) {
        checkController.abort();
    }
    checkRunning = false;
    document.getElementById('checkBtn').classList.remove('hidden');
    document.getElementById('stopCheckBtn').classList.add('hidden');
    document.getElementById('loadingStatus').classList.add('hidden');
}

// Enhanced Bulk Check with multi-site/proxy
let bulkRunning = false;
let bulkStop = false;

async function startBulkCheck() {
    const cardsText = document.getElementById('bulkCards').value.trim();
    const sitesText = document.getElementById('bulkSites').value.trim();
    const proxiesText = document.getElementById('bulkProxies').value.trim();
    
    if (!cardsText) {
        alert('Please enter at least one card');
        return;
    }
    
    const cards = cardsText.split('\n').filter(c => c.trim());
    const sites = sitesText ? sitesText.split('\n').filter(s => s.trim()) : [''];
    const proxies = proxiesText ? proxiesText.split('\n').filter(p => p.trim()) : [''];
    
    if (!cards.length) {
        alert('No valid cards found');
        return;
    }
    
    bulkRunning = true;
    bulkStop = false;
    document.getElementById('startBulkBtn').classList.add('hidden');
    document.getElementById('stopBulkBtn').classList.remove('hidden');
    document.getElementById('bulkProgress').classList.remove('hidden');
    
    let approved = 0, declined = 0, remaining = cards.length;
    let siteIndex = 0, proxyIndex = 0;
    
    for (let i = 0; i < cards.length; i++) {
        if (bulkStop) break;
        
        const card = cards[i].trim();
        const site = sites[siteIndex % sites.length];
        const proxy = proxies[proxyIndex % proxies.length];
        
        document.getElementById('bulkCurrent').textContent = `${i + 1}/${cards.length}`;
        
        try {
            let url = `/process?key=md-tech&cc=${encodeURIComponent(card)}&site=${encodeURIComponent(site)}`;
            if (proxy) url += `&proxy=${encodeURIComponent(proxy)}`;
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.status === 'Approved') approved++;
            else declined++;
            remaining--;
            
            document.getElementById('bulkApproved').textContent = approved;
            document.getElementById('bulkDeclined').textContent = declined;
            document.getElementById('bulkRemaining').textContent = remaining;
            document.getElementById('bulkProgressBar').style.width = `${((i + 1) / cards.length) * 100}%`;
            
            siteIndex++;
            proxyIndex++;
            
        } catch (error) {
            console.error('Error checking card:', error);
            declined++;
            remaining--;
        }
        
        // Small delay between checks
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    bulkRunning = false;
    document.getElementById('startBulkBtn').classList.remove('hidden');
    document.getElementById('stopBulkBtn').classList.add('hidden');
    
    if (bulkStop) {
        alert('Bulk check stopped by user');
    } else {
        alert(`Bulk check complete!\nApproved: ${approved}\nDeclined: ${declined}`);
    }
}

function stopBulkCheck() {
    bulkStop = true;
}

// Advanced settings functions
function restartSystem() {
    if (confirm('Are you sure you want to restart the system?')) {
        fetch('/admin/system/restart', { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                if (data.success) alert('System restart initiated!');
                else alert('Error: ' + data.error);
            });
    }
}

function clearCache() {
    if (confirm('Are you sure you want to clear cache?')) {
        fetch('/admin/system/cache/clear', { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                if (data.success) alert('Cache cleared successfully!');
                else alert('Error: ' + data.error);
            });
    }
}

function downloadBackup() {
    fetch('/admin/backup/download')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const blob = new Blob([JSON.stringify(data.data, null, 2)], {type: 'application/json'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'backup_' + new Date().toISOString().split('T')[0] + '.json';
                a.click();
                URL.revokeObjectURL(url);
            }
        });
}

// API Management functions
function copyApiKey() {
    navigator.clipboard.writeText('md-tech');
    alert('API key copied to clipboard!');
}

function refreshAPIStats() {
    fetch('/admin/stats')
        .then(r => r.json())
        .then(data => {
            document.getElementById('apiTotalRequests').textContent = data.total_requests || 0;
            document.getElementById('apiSuccessRate').textContent = (data.success_rate || 0) + '%';
        });
}

// Auto-refresh API stats
setInterval(refreshAPIStats, 5000);
