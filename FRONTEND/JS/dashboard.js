// ============================================
// DASHBOARD.JS - Dashboard Page Logic
// ============================================

window._categoryTypes = window._categoryTypes || {};

function loadDashboard() {
    var user = getUser();
    if (!user) {
        window.location.href = '/HTML/index.html';
        return;
    }

    var userDisplay = document.getElementById('userDisplay');
    if (userDisplay) {
        var display = user.first_name || user.full_name || user.username || user.email || '';
        userDisplay.textContent = 'Welcome, ' + display;
    }

    loadCategories();
    loadTransactions();
    loadBudgets();
}

function loadCategories() {
    var token = getToken();
    if (!token) return;

    fetch(CONFIG.API_URL + '/categories', { headers: authHeaders() })
    .then(function(response) {
        if (!response.ok) throw new Error('Failed to load categories');
        return response.json();
    })
    .then(function(categories) {
        var map = {};
        categories.forEach(function(cat) { map[cat.category_id] = cat.category_type; });
        window._categoryTypes = map;

        var select = document.getElementById('transCategory');
        if (select) {
            select.innerHTML = '<option value="">Select Category</option>';
            categories.forEach(function(cat) {
                var opt = document.createElement('option');
                opt.value = cat.category_id;
                opt.textContent = cat.category_name;
                select.appendChild(opt);
            });
        }

        var budgetSelect = document.getElementById('budgetCategory');
        if (budgetSelect) {
            budgetSelect.innerHTML = '<option value="">Select Category</option>';
            categories.forEach(function(cat) {
                var opt = document.createElement('option');
                opt.value = cat.category_id;
                opt.textContent = cat.category_name;
                budgetSelect.appendChild(opt);
            });
        }

        var categoryList = document.getElementById('categoryList');
        if (categoryList) {
            categoryList.innerHTML = '';
            categories.forEach(function(cat) {
                var div = document.createElement('div');
                div.className = 'category-item';
                var typeClass = String(cat.category_type || '').toLowerCase();
                div.innerHTML = '<span>' + escapeHtml(cat.category_name) + '</span>'
                    + '<span class="' + typeClass + '">' + escapeHtml(cat.category_type) + '</span>';
                categoryList.appendChild(div);
            });
        }
    })
    .catch(function(error) { console.error('Error loading categories:', error); });
}

function loadTransactions() {
    var token = getToken();
    if (!token) return;

    fetch(CONFIG.API_URL + '/transactions', { headers: authHeaders() })
    .then(function(response) {
        if (!response.ok) throw new Error('Failed to load transactions');
        return response.json();
    })
    .then(function(transactions) {
        var list = document.getElementById('transactionList');
        if (!list) return;

        list.innerHTML = '';
        if (!transactions || !transactions.length) {
            list.innerHTML = '<div class="transaction-item"><span class="muted">No transactions yet.</span></div>';
            var b0 = document.getElementById('balance');
            var i0 = document.getElementById('income');
            var e0 = document.getElementById('expenses');
            if (b0) b0.textContent = '0.00';
            if (i0) i0.textContent = '0.00';
            if (e0) e0.textContent = '0.00';
            return;
        }

        var totalIncome = 0, totalExpense = 0;
        transactions.forEach(function(t) {
            var div = document.createElement('div');
            div.className = 'transaction-item';
            var amount = parseFloat(t.amount);
            if (t.transaction_type === 'Income') totalIncome += amount;
            else totalExpense += amount;
            var amountDisplay = (t.transaction_type === 'Income' ? '+' : '-') + ' ' + amount.toFixed(2);
            var amountClass = t.transaction_type.toLowerCase();
            div.innerHTML = '<span>' + escapeHtml(t.description || t.transaction_type) + '</span>'
                + '<span class="' + amountClass + '">' + escapeHtml(amountDisplay) + '</span>';
            list.appendChild(div);
        });

        var balanceEl = document.getElementById('balance');
        var incomeEl = document.getElementById('income');
        var expenseEl = document.getElementById('expenses');
        if (balanceEl) balanceEl.textContent = (totalIncome - totalExpense).toFixed(2);
        if (incomeEl) incomeEl.textContent = totalIncome.toFixed(2);
        if (expenseEl) expenseEl.textContent = totalExpense.toFixed(2);
    })
    .catch(function(error) { console.error('Error loading transactions:', error); });
}

function loadBudgets() {
    var token = getToken();
    if (!token) return;

    fetch(CONFIG.API_URL + '/budgets', { headers: authHeaders() })
    .then(function(response) {
        if (!response.ok) throw new Error('Failed to load budgets');
        return response.json();
    })
    .then(function(budgets) {
        var list = document.getElementById('budgetList');
        if (!list) return;
        list.innerHTML = '';
        budgets.forEach(function(b) {
            var div = document.createElement('div');
            div.className = 'budget-item';
            var label = escapeHtml(b.category_name);
            if (b.month && b.year) {
                label += ' <small>(' + escapeHtml(b.month) + '/' + escapeHtml(b.year) + ')</small>';
            }
            div.innerHTML = '<span>' + label + '</span>'
                + '<span>' + parseFloat(b.amount).toFixed(2) + '</span>';
            list.appendChild(div);
        });
    })
    .catch(function(error) { console.error('Error loading budgets:', error); });
}

function addTransaction(event) {
    event.preventDefault();
    var token = getToken();
    if (!token) { alert('Please login first.'); return; }

    var data = {
        category_id: document.getElementById('transCategory').value,
        transaction_type: document.getElementById('transType').value,
        amount: document.getElementById('transAmount').value,
        description: document.getElementById('transDesc').value,
        transaction_date: document.getElementById('transDate').value || new Date().toISOString().split('T')[0]
    };

    var btn = null;
    var formEl = document.getElementById('transactionForm');
    if (formEl) btn = formEl.querySelector('button[type="submit"]');
    if (btn) { btn.disabled = true; btn.textContent = 'Adding...'; }

    fetch(CONFIG.API_URL + '/transactions', {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(data)
    })
    .then(function(response) {
        return response.json().then(function(body) { return { status: response.status, body: body }; });
    })
    .then(function(result) {
        if (result.body && result.body.error) {
            alert('Error: ' + result.body.error);
            return;
        }
        var form = document.getElementById('transactionForm');
        if (form) form.reset();
        if (btn) { btn.disabled = false; btn.textContent = 'Add Transaction'; }
        loadTransactions();
        alert('Transaction added successfully!');
    })
    .catch(function(error) {
        console.error('Error adding transaction:', error);
        if (btn) { btn.disabled = false; btn.textContent = 'Add Transaction'; }
        alert('Failed to add transaction.');
    });
}

function addCategory(event) {
    event.preventDefault();
    var token = getToken();
    if (!token) { alert('Please login first.'); return; }

    var data = {
        category_name: document.getElementById('catName').value,
        category_type: document.getElementById('catType').value
    };

    fetch(CONFIG.API_URL + '/categories', {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(data)
    })
    .then(function(response) {
        return response.json().then(function(body) { return { status: response.status, body: body }; });
    })
    .then(function(result) {
        if (result.body && result.body.error) {
            alert('Error: ' + result.body.error);
            return;
        }
        var form = document.getElementById('categoryForm');
        if (form) form.reset();
        loadCategories();
        alert('Category added successfully!');
    })
    .catch(function(error) {
        console.error('Error adding category:', error);
        alert('Failed to add category.');
    });
}

function addBudget(event) {
    event.preventDefault();
    var token = getToken();
    if (!token) { alert('Please login first.'); return; }

    var data = {
        category_id: document.getElementById('budgetCategory').value,
        amount: document.getElementById('budgetAmount').value,
        month: parseInt(document.getElementById('budgetMonth').value),
        year: parseInt(document.getElementById('budgetYear').value)
    };

    fetch(CONFIG.API_URL + '/budgets', {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(data)
    })
    .then(function(response) {
        return response.json().then(function(body) { return { status: response.status, body: body }; });
    })
    .then(function(result) {
        if (result.body && result.body.error) {
            alert('Error: ' + result.body.error);
            return;
        }
        var form = document.getElementById('budgetForm');
        if (form) form.reset();
        loadBudgets();
        alert('Budget added successfully!');
    })
    .catch(function(error) {
        console.error('Error adding budget:', error);
        alert('Failed to add budget.');
    });
}

document.addEventListener('DOMContentLoaded', function() {
    if (!isAuthenticated()) {
        window.location.href = '/HTML/index.html';
        return;
    }

    loadDashboard();

    var transactionForm = document.getElementById('transactionForm');
    if (transactionForm) transactionForm.addEventListener('submit', addTransaction);

    var transCategory = document.getElementById('transCategory');
    if (transCategory) {
        transCategory.addEventListener('change', function() {
            var type = (window._categoryTypes || {})[this.value];
            var typeSelect = document.getElementById('transType');
            if (type && typeSelect) typeSelect.value = type;
        });
    }

    var categoryForm = document.getElementById('categoryForm');
    if (categoryForm) categoryForm.addEventListener('submit', addCategory);

    var budgetForm = document.getElementById('budgetForm');
    if (budgetForm) budgetForm.addEventListener('submit', addBudget);
});

window.loadDashboard = loadDashboard;
window.addTransaction = addTransaction;
window.addCategory = addCategory;
window.addBudget = addBudget;