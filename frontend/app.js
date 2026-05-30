// Base URL of the FastAPI Backend
// - Local development (file://, Live Server, localhost): point to FastAPI at localhost:8000
// - Production (Vercel): use the current origin so new URL() gets a valid absolute URL
const isLocal = window.location.protocol === 'file:' ||
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1';
const API_BASE_URL = isLocal ? 'http://localhost:8000' : window.location.origin;


// Global references to Chart.js instances to allow destruction on update
let barChartInstance = null;
let doughnutChartInstance = null;

// Global state variables
let minDbDate = null;
let maxDbDate = null;

// Initialize the dashboard on page load
document.addEventListener('DOMContentLoaded', async () => {
    console.log("Initializing dashboard...");
    await loadMetadata();
    await refreshAllData();
    setupEventListeners();
});

/**
 * Fetch and load system metadata (min/max transaction dates and unique investors list).
 */
async function loadMetadata() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/dashboard/metadata`);
        if (!response.ok) throw new Error("Failed to fetch metadata");
        
        const metadata = await response.ok ? await response.json() : null;
        if (!metadata) return;

        minDbDate = metadata.min_date;
        maxDbDate = metadata.max_date;

        console.log(`Date range in DB: ${minDbDate} to ${maxDbDate}`);

        // Set default date range filters if inputs are blank
        const startDateInput = document.getElementById('startDate');
        const endDateInput = document.getElementById('endDate');
        
        if (startDateInput && minDbDate) {
            startDateInput.value = minDbDate;
            startDateInput.min = minDbDate;
            startDateInput.max = maxDbDate;
        }
        if (endDateInput && maxDbDate) {
            endDateInput.value = maxDbDate;
            endDateInput.min = minDbDate;
            endDateInput.max = maxDbDate;
        }

        // Populate Investor filter dropdown
        const investorFilter = document.getElementById('investorFilter');
        if (investorFilter && metadata.investors) {
            // Keep first option "Overall"
            investorFilter.innerHTML = '<option value="">Overall (All Investors)</option>';
            metadata.investors.forEach(inv => {
                const option = document.createElement('option');
                option.value = inv.pan;
                option.textContent = `${inv.inv_name} (${inv.pan})`;
                investorFilter.appendChild(option);
            });
        }
    } catch (error) {
        console.error("Error loading metadata:", error);
    }
}

/**
 * Main function to fetch and refresh all reports.
 */
async function refreshAllData() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    console.log(`Refreshing data with range: ${startDate} to ${endDate}`);

    // Trigger parallel fetches for performance optimization
    const promises = [
        fetchMutualFundSummary(startDate, endDate),
        fetchInvestorList(startDate, endDate),
        fetchInvestorPurchaseSummary(startDate, endDate),
        fetchStructuredBreakdown(startDate, endDate)
    ];

    await Promise.all(promises);
}

/**
 * Format currency to Indian Rupees display (₹ 1,23,456.78)
 */
function formatCurrency(value) {
    if (value === null || value === undefined || isNaN(value)) return '₹0.00';
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

/**
 * Format raw numbers with comma separation and 2 decimals
 */
function formatNumber(value) {
    if (value === null || value === undefined || isNaN(value)) return '0.00';
    return new Intl.NumberFormat('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

/**
 * Component 4: Mutual Fund Summary (Metrics + Grid Table)
 */
async function fetchMutualFundSummary(startDate, endDate) {
    const tbody = document.getElementById('tableMfSummary');
    try {
        const url = new URL(`${API_BASE_URL}/api/dashboard/mutual-funds`);
        if (startDate) url.searchParams.append('start_date', startDate);
        if (endDate) url.searchParams.append('end_date', endDate);

        const response = await fetch(url);
        if (!response.ok) throw new Error("Failed to fetch mutual fund summary");
        const data = await response.json();

        // Calculate global statistics based on selection
        let totalInvested = 0;
        let totalUnits = 0;
        
        tbody.innerHTML = '';
        if (data.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-center text-gray-500 py-8">No records found within selection</td></tr>`;
            updateKpiStats(0, 0, 0, 0);
            renderBarChart([]);
            return;
        }

        data.forEach(item => {
            totalInvested += item.total_amount;
            totalUnits += item.total_units;

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="font-medium text-white max-w-xs truncate" title="${item.scheme}">${item.scheme}</td>
                <td class="text-right text-gray-200">${formatCurrency(item.total_amount)}</td>
                <td class="text-right text-gray-300 font-mono">${formatNumber(item.total_units)}</td>
                <td class="text-right text-indigo-300 font-mono font-semibold">${formatCurrency(item.avg_nav)}</td>
            `;
            tbody.appendChild(tr);
        });

        // Compute Average NAV: \sum Amount / \sum Units
        const avgNav = totalUnits > 0 ? (totalInvested / totalUnits) : 0;
        updateKpiStats(totalInvested, totalUnits, avgNav, data.length);

        // Update visual Bar chart
        renderBarChart(data);

    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="4" class="text-center text-red-400 py-8">Error loading data: ${error.message}</td></tr>`;
        console.error(error);
    }
}

/**
 * Component 3: Investor List with Purchase Details
 */
async function fetchInvestorList(startDate, endDate) {
    const tbody = document.getElementById('tableInvestorList');
    try {
        const url = new URL(`${API_BASE_URL}/api/dashboard/investors`);
        if (startDate) url.searchParams.append('start_date', startDate);
        if (endDate) url.searchParams.append('end_date', endDate);

        const response = await fetch(url);
        if (!response.ok) throw new Error("Failed to fetch investor list");
        const data = await response.json();

        tbody.innerHTML = '';
        if (data.length === 0) {
            tbody.innerHTML = `<tr><td colspan="3" class="text-center text-gray-500 py-8">No records found within selection</td></tr>`;
            renderDoughnutChart([]);
            return;
        }

        data.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="font-mono text-gray-300 font-medium">${item.pan}</td>
                <td class="text-gray-200">${item.inv_name}</td>
                <td class="text-right text-emerald-400 font-mono font-semibold">${formatCurrency(item.total_amount)}</td>
            `;
            tbody.appendChild(tr);
        });

        // Update visual Doughnut chart
        renderDoughnutChart(data);

    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="3" class="text-center text-red-400 py-8">Error loading data: ${error.message}</td></tr>`;
        console.error(error);
    }
}

/**
 * Component 1: Investor-wise Purchase Summary per Mutual Fund
 */
async function fetchInvestorPurchaseSummary(startDate, endDate) {
    const tbody = document.getElementById('tableInvestorPurchase');
    const pan = document.getElementById('investorFilter').value;

    try {
        const url = new URL(`${API_BASE_URL}/api/dashboard/investor-funds`);
        if (startDate) url.searchParams.append('start_date', startDate);
        if (endDate) url.searchParams.append('end_date', endDate);
        if (pan) url.searchParams.append('pan', pan);

        const response = await fetch(url);
        if (!response.ok) throw new Error("Failed to fetch investor-wise summary");
        const data = await response.json();

        tbody.innerHTML = '';
        if (data.length === 0) {
            tbody.innerHTML = `<tr><td colspan="3" class="text-center text-gray-500 py-8">No purchase details available for selection</td></tr>`;
            return;
        }

        data.forEach(item => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="font-medium text-white max-w-xs truncate" title="${item.scheme}">${item.scheme}</td>
                <td class="text-right text-gray-200">${formatCurrency(item.total_amount)}</td>
                <td class="text-right text-gray-300 font-mono">${formatNumber(item.total_units)}</td>
            `;
            tbody.appendChild(tr);
        });

    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="3" class="text-center text-red-400 py-8">Error loading data: ${error.message}</td></tr>`;
        console.error(error);
    }
}

/**
 * Component 2: Mutual Fund-wise Summary per Investor (Collapsible Tree Grid)
 */
async function fetchStructuredBreakdown(startDate, endDate) {
    const tbody = document.getElementById('tableFundInvestors');
    try {
        const url = new URL(`${API_BASE_URL}/api/dashboard/fund-investors`);
        if (startDate) url.searchParams.append('start_date', startDate);
        if (endDate) url.searchParams.append('end_date', endDate);

        const response = await fetch(url);
        if (!response.ok) throw new Error("Failed to fetch structured breakdown");
        const flatData = await response.json();

        tbody.innerHTML = '';
        if (flatData.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-center text-gray-500 py-8">No records found within selection</td></tr>`;
            return;
        }

        // Group flat database rows by mutual fund scheme name
        const schemesMap = {};
        flatData.forEach(row => {
            const scheme = row.scheme;
            if (!schemesMap[scheme]) {
                schemesMap[scheme] = {
                    total_amount: 0.0,
                    total_units: 0.0,
                    investors: []
                };
            }
            schemesMap[scheme].total_amount += row.total_amount;
            schemesMap[scheme].total_units += row.total_units;
            schemesMap[scheme].investors.push({
                pan: row.pan,
                inv_name: row.inv_name,
                amount: row.total_amount,
                units: row.total_units
            });
        });

        let idx = 0;
        for (const schemeName in schemesMap) {
            idx++;
            const schemeData = schemesMap[schemeName];
            const uniqueRowId = `scheme-row-${idx}`;
            const childRowId = `child-row-${idx}`;

            // Create primary Mutual Fund row
            const trScheme = document.createElement('tr');
            trScheme.className = 'cursor-pointer hover:bg-slate-800/60 transition';
            trScheme.setAttribute('data-target', childRowId);
            trScheme.innerHTML = `
                <td class="text-center text-indigo-400 font-bold w-8">
                    <i class="fa-solid fa-chevron-right transition-transform duration-200" id="caret-${idx}"></i>
                </td>
                <td class="font-semibold text-white truncate max-w-xs" title="${schemeName}">${schemeName}</td>
                <td class="text-right text-indigo-300 font-mono font-bold">${formatCurrency(schemeData.total_amount)}</td>
                <td class="text-right text-gray-300 font-mono">${formatNumber(schemeData.total_units)}</td>
            `;
            tbody.appendChild(trScheme);

            // Create nested Collapsible Row of Buyers
            const trBuyers = document.createElement('tr');
            trBuyers.id = childRowId;
            trBuyers.className = 'hidden bg-slate-900/40';
            
            // Build sub-table containing list of individual buyers
            let buyersListHtml = '';
            schemeData.investors.forEach(buyer => {
                buyersListHtml += `
                    <div class="grid grid-cols-12 text-xs py-2 px-4 border-b border-gray-800/40 hover:bg-indigo-600/5 transition">
                        <div class="col-span-3 font-mono text-gray-400">${buyer.pan}</div>
                        <div class="col-span-4 text-gray-300">${buyer.inv_name}</div>
                        <div class="col-span-3 text-right text-emerald-400 font-mono font-medium">${formatCurrency(buyer.amount)}</div>
                        <div class="col-span-2 text-right text-gray-400 font-mono">${formatNumber(buyer.units)}</div>
                    </div>
                `;
            });

            trBuyers.innerHTML = `
                <td></td>
                <td colspan="3" class="p-0">
                    <div class="border-l-2 border-indigo-500 pl-4 py-2 bg-darkBg/30">
                        <div class="grid grid-cols-12 text-[10px] uppercase font-bold text-gray-500 tracking-wider pb-1.5 px-4 border-b border-gray-800">
                            <div class="col-span-3">Buyer PAN</div>
                            <div class="col-span-4">Buyer Name</div>
                            <div class="col-span-3 text-right">Amount (₹)</div>
                            <div class="col-span-2 text-right">Units</div>
                        </div>
                        ${buyersListHtml}
                    </div>
                </td>
            `;
            tbody.appendChild(trBuyers);

            // Add interactivity to toggle details on clicking scheme rows
            trScheme.addEventListener('click', () => {
                const targetRow = document.getElementById(childRowId);
                const caret = document.getElementById(`caret-${idx}`);
                if (targetRow.classList.contains('hidden')) {
                    targetRow.classList.remove('hidden');
                    caret.classList.add('rotate-90');
                } else {
                    targetRow.classList.add('hidden');
                    caret.classList.remove('rotate-90');
                }
            });
        }

    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="4" class="text-center text-red-400 py-8">Error loading data: ${error.message}</td></tr>`;
        console.error(error);
    }
}

/**
 * Update top KPI Metric displays
 */
function updateKpiStats(totalAmt, totalUnits, avgNav, fundsCount) {
    document.getElementById('statTotalInvested').textContent = formatCurrency(totalAmt);
    document.getElementById('statTotalUnits').textContent = formatNumber(totalUnits);
    document.getElementById('statAvgNav').textContent = formatCurrency(avgNav);
    document.getElementById('statUniqueFunds').textContent = fundsCount;
}

/**
 * Configure global UI action event listeners.
 */
function setupEventListeners() {
    // Refresh Button Click
    document.getElementById('refreshBtn').addEventListener('click', async () => {
        const refreshIcon = document.querySelector('#refreshBtn i');
        refreshIcon.classList.add('fa-spin');
        await refreshAllData();
        setTimeout(() => refreshIcon.classList.remove('fa-spin'), 600);
    });

    // Date Range Picker Changes
    document.getElementById('startDate').addEventListener('change', refreshAllData);
    document.getElementById('endDate').addEventListener('change', refreshAllData);

    // Component 1 Investor dropdown filter
    document.getElementById('investorFilter').addEventListener('change', () => {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        fetchInvestorPurchaseSummary(startDate, endDate);
    });
}

/**
 * Chart.js Top Mutual Funds (Bar Chart)
 */
function renderBarChart(data) {
    const ctx = document.getElementById('barChartFunds').getContext('2d');
    
    // Destroy previous instance to avoid visual overlapping and memory leak
    if (barChartInstance) {
        barChartInstance.destroy();
    }

    if (data.length === 0) return;

    // Slice to top 5 funds for neat display
    const topFunds = data.slice(0, 5);
    const labels = topFunds.map(f => f.scheme.length > 25 ? f.scheme.substring(0, 22) + '...' : f.scheme);
    const values = topFunds.map(f => f.total_amount);

    barChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Investment (₹)',
                data: values,
                backgroundColor: 'rgba(99, 102, 241, 0.4)',
                borderColor: '#6366f1',
                borderWidth: 2,
                borderRadius: 8,
                hoverBackgroundColor: 'rgba(99, 102, 241, 0.65)',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Investment: ${formatCurrency(context.raw)}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#94a3b8',
                        font: { size: 9 },
                        callback: function(value) {
                            return '₹' + formatNumber(value);
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#94a3b8',
                        font: { size: 9 }
                    }
                }
            }
        }
    });
}

/**
 * Chart.js Investor Asset Allocation (Doughnut Chart)
 */
function renderDoughnutChart(data) {
    const ctx = document.getElementById('doughnutChartInvestors').getContext('2d');

    if (doughnutChartInstance) {
        doughnutChartInstance.destroy();
    }

    if (data.length === 0) return;

    // Display all or top 6 investors, group remaining as "Others"
    const displayCount = 6;
    let chartData = [];
    let chartLabels = [];

    if (data.length <= displayCount) {
        chartData = data.map(i => i.total_amount);
        chartLabels = data.map(i => i.inv_name);
    } else {
        const top = data.slice(0, displayCount - 1);
        chartData = top.map(i => i.total_amount);
        chartLabels = top.map(i => i.inv_name);
        
        const othersAmt = data.slice(displayCount - 1).reduce((sum, item) => sum + item.total_amount, 0);
        chartData.push(othersAmt);
        chartLabels.push('Others');
    }

    const colors = [
        '#6366f1', // Indigo
        '#10b981', // Emerald
        '#f59e0b', // Amber
        '#ec4899', // Pink
        '#3b82f6', // Blue
        '#8b5cf6', // Violet
        '#64748b'  // Slate for Others
    ];

    doughnutChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: chartLabels,
            datasets: [{
                data: chartData,
                backgroundColor: colors.slice(0, chartLabels.length),
                borderWidth: 2,
                borderColor: '#0f172a',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#94a3b8',
                        font: { size: 9 },
                        boxWidth: 12
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return ` ${context.label}: ${formatCurrency(context.raw)}`;
                        }
                    }
                }
            },
            cutout: '65%'
        }
    });
}
