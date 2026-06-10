// =========================================================================
// AuraAnalytics - Executive Dashboard Controller
// =========================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Check if analytical data is loaded
    if (typeof ANALYTICS_DATA === 'undefined') {
        console.error("Analytics data not found. Please run the pipeline script first.");
        document.body.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; background-color: #090d16; color: white; font-family: sans-serif;">
                <i class="fa-solid fa-triangle-exclamation" style="font-size: 3rem; color: #ef4444; margin-bottom: 1rem;"></i>
                <h2>Data Source Missing</h2>
                <p style="color: #94a3b8; margin-top: 0.5rem;">Please run the python pipeline first: <code>python src/run_pipeline.py</code></p>
            </div>
        `;
        return;
    }

    // Initialize Dashboard Application
    initApp();
});

// Marketing Playbooks Repository
const PLAYBOOKS = {
    'Champions': {
        desc: "Your most valuable customers. They buy frequently, spend heavily, and purchased very recently. They love your brand and drive your highest margins.",
        actions: [
            "Reward with exclusive early access to new product launches and VIP collections.",
            "Upsell premium, high-ticket items and cross-sell complementary categories.",
            "Enroll in advocate/referral programs and ask for written or video testimonials."
        ],
        riskLevel: "Low Risk",
        riskClass: "low-risk"
    },
    'Loyal Customers': {
        desc: "Regular, high-value customers who buy consistently. They are highly responsive to marketing campaigns and brand value.",
        actions: [
            "Offer personalized loyalty rewards, tier upgrades, or points multipliers.",
            "Cross-sell products based on historical purchase categories.",
            "Send personalized thank-you messages and request reviews."
        ],
        riskLevel: "Low Risk",
        riskClass: "low-risk"
    },
    'Potential Loyalists': {
        desc: "Recent buyers who spent average/above-average amounts and have made multiple purchases. They represent the growth pipeline.",
        actions: [
            "Recommend product bundles or subscribe-and-save programs.",
            "Offer trial membership access to VIP shipping benefits.",
            "Cross-sell top-rated products in favorite categories to solidify loyalty."
        ],
        riskLevel: "Low Risk",
        riskClass: "low-risk"
    },
    'New Customers': {
        desc: "Customers who made their first transaction recently. High potential, but their relationship with your brand is not yet established.",
        actions: [
            "Trigger a personalized welcome email series showcasing brand story and quality.",
            "Provide a time-sensitive discount code on their second order to build momentum.",
            "Solicit immediate feedback on their purchasing and delivery experience."
        ],
        riskLevel: "Low Risk",
        riskClass: "low-risk"
    },
    'Promising': {
        desc: "Recent buyers who spent low-value amounts on their initial purchases. They are testing the waters.",
        actions: [
            "Recommend low-barrier, highly-reviewed entry items and accessories.",
            "Send target promotions featuring customer testimonials of similar products.",
            "Offer limited-time free shipping to prompt a second order."
        ],
        riskLevel: "Low Risk",
        riskClass: "low-risk"
    },
    'Need Attention': {
        desc: "Above-average recency and frequency, but their buying frequency is dropping. They are in the transition zone.",
        actions: [
            "Send time-limited reactivation discounts ('We want you back').",
            "Recommend trending products based on their past purchase category.",
            "Trigger customer satisfaction surveys to identify and resolve friction."
        ],
        riskLevel: "Moderate Risk",
        riskClass: "med-risk"
    },
    'About to Sleep': {
        desc: "Below average recency and frequency. They are slipping away and will hibernate soon if not engaged.",
        actions: [
            "Re-engage with personalized content highlighting 'what you missed'.",
            "Offer a higher-value reactivation discount or free-gift-with-purchase.",
            "Highlight new arrivals and top catalog selections."
        ],
        riskLevel: "Moderate Risk",
        riskClass: "med-risk"
    },
    'At Risk': {
        desc: "High-value customers who purchased frequently and spent heavily historically, but have not made any purchases recently.",
        actions: [
            "Deploy aggressive win-back deals and high-value discount vouchers.",
            "Trigger automated exit surveys to capture feedback on product or service issues.",
            "Personalize outreach email recommendations based on historical VIP purchases."
        ],
        riskLevel: "High Risk",
        riskClass: "high-risk"
    },
    "Can't Lose Them": {
        desc: "Historically your biggest spenders and most frequent buyers, but they have not interacted with your brand in a long time. Immediate threat of permanent churn.",
        actions: [
            "Execute direct executive outreach or assign a dedicated account manager.",
            "Extend exclusive 'Lifetime Loyalty' extension discounts or free premium upgrades.",
            "Conduct one-on-one feedback interviews to resolve outstanding pain points."
        ],
        riskLevel: "High Risk",
        riskClass: "high-risk"
    },
    'Hibernating': {
        desc: "Your lowest-value inactive customers. Low spend, low frequency, and long time since last purchase. Low priority for expensive campaigns.",
        actions: [
            "Add to automated low-cost reactivation email drip sequences.",
            "Offer basic stock clearance discounts and seasonal group promotions.",
            "Avoid expensive, high-touch channels (like direct mail or SMS)."
        ],
        riskLevel: "High Risk",
        riskClass: "high-risk"
    }
};

let activeCharts = {};

function initApp() {
    // 1. Render Last Updated Time & Badge
    document.getElementById('last-updated-time').textContent = `Last update: ${ANALYTICS_DATA.last_updated}`;
    
    // 2. Set current date in header
    const options = { month: 'long', year: 'numeric' };
    document.getElementById('current-date-badge').innerText = new Date().toLocaleDateString('en-US', options);

    // 3. Setup Tab Navigation
    setupNavigation();

    // 4. Load KPI statistics
    loadKPIs();

    // 5. Render Overview Charts
    renderOverviewCharts();

    // 6. Render RFM Data
    renderRFMData();

    // 7. Render Churn and CLV Quadrants
    renderChurnCLVData();

    // 8. Render Product Leaderboard
    renderProductLeaderboard();
}

// ---------------------------------------------------------
// Navigation & Routing
// ---------------------------------------------------------
function setupNavigation() {
    const navButtons = [
        { btn: 'btn-overview', section: 'overview-section' },
        { btn: 'btn-segmentation', section: 'segmentation-section' },
        { btn: 'btn-clv-churn', section: 'clv-churn-section' },
        { btn: 'btn-products', section: 'products-section' }
    ];

    navButtons.forEach(item => {
        const buttonEl = document.getElementById(item.btn);
        if (buttonEl) {
            buttonEl.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Set active class on menu buttons
                navButtons.forEach(x => document.getElementById(x.btn).classList.remove('active'));
                buttonEl.classList.add('active');
                
                // Toggle sections with transitions
                navButtons.forEach(x => {
                    const secEl = document.getElementById(x.section);
                    secEl.classList.remove('active');
                });
                
                const activeSection = document.getElementById(item.section);
                activeSection.classList.add('active');
                
                // Re-render/resize charts if needed
                window.dispatchEvent(new Event('resize'));
            });
        }
    });
}

// ---------------------------------------------------------
// KPI Summary Loading
// ---------------------------------------------------------
function loadKPIs() {
    const kpis = ANALYTICS_DATA.kpis;
    
    document.getElementById('val-revenue').textContent = formatCurrency(kpis.total_revenue);
    document.getElementById('val-customers').textContent = formatInteger(kpis.total_customers);
    document.getElementById('val-aov').textContent = formatCurrency(kpis.aov);
    document.getElementById('val-churn').textContent = (kpis.overall_churn_rate * 100).toFixed(1) + '%';
    document.getElementById('val-clv').textContent = formatCurrency(kpis.avg_clv);
}

// ---------------------------------------------------------
// Overview Visualizations (Line & Bar)
// ---------------------------------------------------------
function renderOverviewCharts() {
    const trends = ANALYTICS_DATA.monthly_trends;
    const countries = ANALYTICS_DATA.countries;
    
    const months = trends.map(t => t.month);
    const revenue = trends.map(t => t.revenue);
    const orders = trends.map(t => t.orders);
    
    // Line Chart: Revenue & Orders Dual Axis
    const trendCtx = document.getElementById('revenueTrendChart').getContext('2d');
    
    // Create subtle gradient for fills
    const revGradient = trendCtx.createLinearGradient(0, 0, 0, 300);
    revGradient.addColorStop(0, 'rgba(99, 102, 241, 0.25)');
    revGradient.addColorStop(1, 'rgba(99, 102, 241, 0.00)');
    
    activeCharts['revenueTrend'] = new Chart(trendCtx, {
        type: 'line',
        data: {
            labels: months,
            datasets: [
                {
                    label: 'Revenue ($)',
                    data: revenue,
                    borderColor: '#6366f1',
                    borderWidth: 3,
                    pointBackgroundColor: '#6366f1',
                    pointBorderColor: '#ffffff',
                    pointHoverRadius: 6,
                    fill: true,
                    backgroundColor: revGradient,
                    yAxisID: 'y'
                },
                {
                    label: 'Orders',
                    data: orders,
                    borderColor: '#10b981',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    pointBackgroundColor: '#10b981',
                    pointHoverRadius: 5,
                    fill: false,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#94a3b8', font: { family: 'Inter' } }
                },
                tooltip: {
                    backgroundColor: '#1e293b',
                    titleColor: '#ffffff',
                    bodyColor: '#94a3b8',
                    borderColor: 'rgba(255,255,255,0.08)',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: { color: '#94a3b8' }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: { 
                        color: '#94a3b8',
                        callback: function(value) { return '$' + formatInteger(value); }
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    });

    // Horizontal Bar Chart: Country Revenue
    const countryLabels = countries.map(c => c.country);
    const countryRevenue = countries.map(c => c.revenue);
    
    const countryCtx = document.getElementById('countryRevenueChart').getContext('2d');
    
    activeCharts['countryRevenue'] = new Chart(countryCtx, {
        type: 'bar',
        data: {
            labels: countryLabels,
            datasets: [{
                label: 'Revenue ($)',
                data: countryRevenue,
                backgroundColor: 'rgba(6, 182, 212, 0.75)',
                borderColor: '#06b6d4',
                borderWidth: 1.5,
                borderRadius: 8,
                hoverBackgroundColor: '#06b6d4'
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1e293b',
                    borderColor: 'rgba(255,255,255,0.08)',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: { 
                        color: '#94a3b8',
                        callback: function(value) { return '$' + formatInteger(value); }
                    }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    });
}

// ---------------------------------------------------------
// RFM Segmentation & Playbooks
// ---------------------------------------------------------
function renderRFMData() {
    const segments = ANALYTICS_DATA.segments;
    
    // Donut Chart: Segment Share
    const segNames = segments.map(s => s.segment);
    const segCounts = segments.map(s => s.count);
    
    // Curated vibrant segment color array matching our design system
    const segColors = [
        '#6366f1', // Champions
        '#10b981', // Loyal Customers
        '#06b6d4', // Potential Loyalists
        '#8b5cf6', // New Customers
        '#f59e0b', // Promising
        '#ec4899', // Need Attention
        '#64748b', // About to Sleep
        '#ef4444', // At Risk
        '#f43f5e', // Can't Lose Them
        '#334155'  // Hibernating
    ];

    const donutCtx = document.getElementById('segmentDonutChart').getContext('2d');
    
    activeCharts['segmentDonut'] = new Chart(donutCtx, {
        type: 'doughnut',
        data: {
            labels: segNames,
            datasets: [{
                data: segCounts,
                backgroundColor: segColors,
                borderWidth: 2,
                borderColor: '#0f172a',
                hoverOffset: 12
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#94a3b8',
                        boxWidth: 12,
                        padding: 12,
                        font: { size: 10, family: 'Inter' }
                    }
                },
                tooltip: {
                    backgroundColor: '#1e293b',
                    borderColor: 'rgba(255,255,255,0.08)',
                    borderWidth: 1
                }
            },
            cutout: '65%'
        }
    });

    // Populate Segment Profiles Table
    const tbody = document.getElementById('tbody-segments');
    tbody.innerHTML = '';
    
    segments.forEach((s, idx) => {
        const tr = document.createElement('tr');
        tr.style.cursor = 'pointer';
        tr.addEventListener('click', () => {
            document.getElementById('playbook-segment-selector').value = s.segment;
            loadPlaybook(s.segment);
            // Smooth scroll to playbook
            document.querySelector('.playbook-card').scrollIntoView({ behavior: 'smooth' });
        });

        tr.innerHTML = `
            <td>
                <span class="segment-pill text-bold" style="background: ${hexToRgba(segColors[idx], 0.15)}; color: ${segColors[idx]}; border: 1px solid ${hexToRgba(segColors[idx], 0.25)};">
                    ${s.segment}
                </span>
            </td>
            <td class="text-bold">${formatInteger(s.count)}</td>
            <td>${(s.pct * 100).toFixed(1)}%</td>
            <td class="text-bold">${formatCurrency(s.avg_monetary)}</td>
            <td>${s.avg_recency} days</td>
            <td>${s.avg_frequency} orders</td>
            <td class="text-success text-bold">${formatCurrency(s.avg_clv)}</td>
        `;
        tbody.appendChild(tr);
    });

    // Setup Interactive Segment Selector in Playbook
    const selector = document.getElementById('playbook-segment-selector');
    selector.innerHTML = '';
    
    segments.forEach(s => {
        const option = document.createElement('option');
        option.value = s.segment;
        option.textContent = s.segment;
        selector.appendChild(option);
    });

    selector.addEventListener('change', (e) => {
        loadPlaybook(e.target.value);
    });

    // Load Default Playbook (Champions)
    if (segments.length > 0) {
        loadPlaybook(segments[0].segment);
    }
}

function loadPlaybook(segmentName) {
    const segments = ANALYTICS_DATA.segments;
    const segmentData = segments.find(s => s.segment === segmentName);
    const playbook = PLAYBOOKS[segmentName] || PLAYBOOKS['Champions'];
    
    if (!segmentData) return;
    
    document.getElementById('playbook-segment-name').textContent = segmentName;
    document.getElementById('playbook-size').textContent = `${formatInteger(segmentData.count)} Customers (${(segmentData.pct*100).toFixed(1)}% share)`;
    
    const riskBadge = document.getElementById('playbook-risk');
    riskBadge.textContent = `${playbook.riskLevel} (${(segmentData.avg_churn_prob*100).toFixed(1)}% Avg Churn Risk)`;
    riskBadge.className = `badge ${playbook.riskClass}`;
    
    document.getElementById('playbook-desc').textContent = playbook.desc;
    
    const actionsList = document.getElementById('playbook-actions');
    actionsList.innerHTML = '';
    playbook.actions.forEach(action => {
        const li = document.createElement('li');
        li.textContent = action;
        actionsList.appendChild(li);
    });
}

// ---------------------------------------------------------
// Churn Analytics & Quadrants
// ---------------------------------------------------------
function renderChurnCLVData() {
    const vips = ANALYTICS_DATA.top_risk_vips;
    const segments = ANALYTICS_DATA.segments;
    
    // 1. VIP Churn Alerts Table
    const tbody = document.getElementById('tbody-churn-alerts');
    tbody.innerHTML = '';
    
    document.getElementById('churn-alert-count').textContent = `${vips.length} Alerts`;
    
    if (vips.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No immediate high-value churn threats identified.</td></tr>`;
    } else {
        vips.forEach(v => {
            const tr = document.createElement('tr');
            
            // Map segment colors for badges in churn list
            let pillColor = '#94a3b8';
            if (v.segment === 'Champions') pillColor = '#6366f1';
            else if (v.segment === 'Loyal Customers') pillColor = '#10b981';
            else if (v.segment === "Can't Lose Them") pillColor = '#f43f5e';
            
            tr.innerHTML = `
                <td class="text-bold">${v.customer_id}</td>
                <td>
                    <span class="segment-pill" style="background: ${hexToRgba(pillColor, 0.15)}; color: ${pillColor}; border: 1px solid ${hexToRgba(pillColor, 0.25)};">
                        ${v.segment}
                    </span>
                </td>
                <td class="text-bold text-danger">${v.recency} days</td>
                <td class="text-bold">${formatCurrency(v.monetary)}</td>
                <td>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span class="text-danger text-bold">${(v.churn_prob * 100).toFixed(0)}%</span>
                        <div style="width: 50px; background-color: rgba(255,255,255,0.05); height: 6px; border-radius: 3px; overflow: hidden;">
                            <div style="width: ${v.churn_prob * 100}%; background-color: var(--color-danger); height: 100%;"></div>
                        </div>
                    </div>
                </td>
                <td class="text-success text-bold">${formatCurrency(v.clv)}</td>
                <td>
                    <button class="btn-action-retention" onclick="triggerRetentionCampaign(${v.customer_id})">
                        Re-engage
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    // 2. Churn-Value Matrix Calculations
    // We map segments onto the 2x2 matrix:
    // - High Value / Low Risk (HVLR): Champions, Loyal Customers
    // - High Value / High Risk (HVHR): At Risk, Can't Lose Them
    // - Low Value / Low Risk (LVLR): Potential Loyalists, New Customers, Promising
    // - Low Value / High Risk (LVHR): Need Attention, About to Sleep, Hibernating
    
    let hvlr = 0, hvhr = 0, lvlr = 0, lvhr = 0;
    
    segments.forEach(s => {
        if (['Champions', 'Loyal Customers'].includes(s.segment)) {
            hvlr += s.count;
        } else if (['At Risk', "Can't Lose Them"].includes(s.segment)) {
            hvhr += s.count;
        } else if (['Potential Loyalists', 'New Customers', 'Promising'].includes(s.segment)) {
            lvlr += s.count;
        } else {
            lvhr += s.count;
        }
    });
    
    document.getElementById('stat-hvlr').textContent = formatInteger(hvlr);
    document.getElementById('stat-hvhr').textContent = formatInteger(hvhr);
    document.getElementById('stat-lvlr').textContent = formatInteger(lvlr);
    document.getElementById('stat-lvhr').textContent = formatInteger(lvhr);
}

// ---------------------------------------------------------
// Product Insights
// ---------------------------------------------------------
function renderProductLeaderboard() {
    const products = ANALYTICS_DATA.top_products;
    
    // Render Horizontal Bar Chart
    const prodCtx = document.getElementById('productRevenueChart').getContext('2d');
    
    // Take Top 8 for the bar chart so it doesn't get cluttered
    const top8Products = products.slice(0, 8);
    const prodLabels = top8Products.map(p => p.description.length > 20 ? p.description.substring(0, 20) + '...' : p.description);
    const prodRevenues = top8Products.map(p => p.revenue);
    
    activeCharts['productRevenue'] = new Chart(prodCtx, {
        type: 'bar',
        data: {
            labels: prodLabels,
            datasets: [{
                label: 'Revenue ($)',
                data: prodRevenues,
                backgroundColor: 'rgba(139, 92, 246, 0.75)',
                borderColor: '#8b5cf6',
                borderWidth: 1.5,
                borderRadius: 8,
                hoverBackgroundColor: '#8b5cf6'
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1e293b',
                    borderColor: 'rgba(255,255,255,0.08)',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.03)' },
                    ticks: { 
                        color: '#94a3b8',
                        callback: function(value) { return '$' + formatInteger(value); }
                    }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8' }
                }
            }
        }
    });

    // Populate Detailed Product Table
    const tbody = document.getElementById('tbody-products');
    tbody.innerHTML = '';
    
    products.forEach(p => {
        const tr = document.createElement('tr');
        const avgPrice = p.units_sold > 0 ? (p.revenue / p.units_sold) : 0.0;
        
        tr.innerHTML = `
            <td class="text-bold">${p.stock_code}</td>
            <td>${p.description}</td>
            <td class="text-bold">${formatCurrency(p.revenue)}</td>
            <td class="text-bold text-cyan">${formatInteger(p.units_sold)}</td>
            <td>${formatCurrency(avgPrice)}</td>
        `;
        tbody.appendChild(tr);
    });
}

// ---------------------------------------------------------
// Helper Utilities
// ---------------------------------------------------------
function formatCurrency(val) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
}

function formatInteger(val) {
    return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(val);
}

function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// Retention Action Toast trigger
window.triggerRetentionCampaign = function(customerId) {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toast-message');
    
    toastMessage.textContent = `Retention workflow triggered for Customer #${customerId}!`;
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3500);
};
