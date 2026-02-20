let currentTargetRole = '';
let currentParentUsername = ''; // To track who the selected parent is
const ROLE_LEVEL = { Superadmin: 100, Subadmin: 90, Admin: 80, Miniadmin: 70, Master: 60, Super: 50, Agent: 40, Client: 30 };
const headerEl = document.querySelector('.custom-header .fw-bold');
const LOGGED_IN_USERNAME = headerEl.dataset.username;
// 1. GLOBAL HELPERS
function initDropdowns(container) {
    container.querySelectorAll('[data-bs-toggle="dropdown"]').forEach(el => {
        new bootstrap.Dropdown(el, { popperConfig: { strategy: 'fixed' } });
    });
}

function handleCreateClick(role, myLevel, targetLevel) {
    currentTargetRole = role;
    const gap = myLevel - targetLevel;
    if (gap === 10) {
        loadRegistrationForm(role, LOGGED_IN_USERNAME);
        return;
    }
    const parentRole = Object.keys(ROLE_LEVEL).find(key => ROLE_LEVEL[key] === (targetLevel + 10));
    fetch(`/get-uplines/${parentRole.toLowerCase()}/`)
        .then(res => res.json())
        .then(users => {
            const select = document.getElementById("parentSelect");
            select.innerHTML = '<option disabled selected>-- Select --</option>';
            users.forEach(u => { select.innerHTML += `<option value="${u.username}">${u.username}</option>`; });
            new bootstrap.Modal(document.getElementById('uplineModal')).show();
        });
}

function proceedToRegistration() {
    const parent = document.getElementById('parentSelect').value;
    if (!parent || parent.includes('--')) return alert("Select a parent");
    bootstrap.Modal.getInstance(document.getElementById('uplineModal')).hide();
    loadRegistrationForm(currentTargetRole, parent);
}
function toggleShareTypeFields() {
    document.querySelectorAll('[data-share-type]').forEach(field => {
        const shareType = field.dataset.shareType; // Get the share_type value
        const input = field.querySelector('input[name="parent_match_share"]');
        if (shareType === "FIXED") {
            input.setAttribute('readonly', true);
        } else {
            input.removeAttribute('readonly');
        }
    });
}
document.addEventListener('DOMContentLoaded', toggleShareTypeFields);
function loadRegistrationForm(role, parent) {
    currentParentUsername = parent; // Save for the POST payload
    const dynamicDiv = document.getElementById('dynamicContent');
    document.getElementById('dashboardContent').style.display = 'none';
    dynamicDiv.style.display = 'block';
    dynamicDiv.innerHTML = '<div class="text-center mt-5"><div class="spinner-border"></div></div>';
    
    fetch(`/get-registration-form/?role=${role}&parent=${parent}`)
        .then(res => res.text())
        .then(html => { dynamicDiv.innerHTML = html; initDropdowns(dynamicDiv); toggleCommissionFields(); });
}

// 2. EVENT LISTENERS
document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.getElementById('sidebar');
    const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

    // Sidebar Toggle
    document.getElementById('sidebarToggle').addEventListener('click', (e) => {
        e.stopPropagation();
        sidebar.classList.toggle('active');
    });

    // Close sidebar on click outside
    document.addEventListener('click', (e) => {
        if (e.target.closest('[data-bs-toggle="dropdown"]') || e.target.closest('.dropdown-menu')) return;
        if (window.innerWidth <= 768 && !sidebar.contains(e.target)) sidebar.classList.remove('active');
    });

    // Role AJAX Table
    document.querySelectorAll('.role-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const role = this.dataset.role;
            document.getElementById('dashboardContent').style.display = 'none';
            const dynamic = document.getElementById('dynamicContent');
            dynamic.style.display = 'block';
            dynamic.innerHTML = '<div class="text-center mt-5"><div class="spinner-border"></div></div>';
            
            fetch(`/get-downline/${role.toLowerCase()}/`)
                .then(res => res.text())
                .then(html => { dynamic.innerHTML = html; initDropdowns(dynamic); 
                    const activeBtn = dynamic.querySelector('.filter-active');
        const inactiveBtn = dynamic.querySelector('.filter-inactive');

        // Select table rows
        const rows = dynamic.querySelectorAll('#usersTable tbody tr');

        if (!activeBtn || !inactiveBtn || rows.length === 0) {
            console.error("Buttons or table rows not found!");
            return;
        }

        // Filter functions (trim + lowercase to avoid Django template quirks)
        const showActiveUsers = () => {
            rows.forEach(row => {
                row.style.display = row.dataset.active?.trim().toLowerCase() === 'true' ? '' : 'none';
            });
        };

        const showInactiveUsers = () => {
            rows.forEach(row => {
                row.style.display = row.dataset.active?.trim().toLowerCase() === 'false' ? '' : 'none';
            });
        };

        // Attach event listeners
        activeBtn.addEventListener('click', showActiveUsers);
        inactiveBtn.addEventListener('click', showInactiveUsers);

        // Show active users by default
        showActiveUsers();

                });
        });
    });

    // Dashboard View Switch
    document.getElementById('defaultDashboardView').addEventListener('click', () => {
        document.getElementById('dashboardContent').style.display = 'block';
        document.getElementById('dynamicContent').style.display = 'none';
    });

    // GLOBAL FORM SUBMIT (Fixes the Commission Type Error)
    document.addEventListener('submit', function(e) {
        if (e.target.id !== 'newUserForm') return;
        e.preventDefault();

        const formData = new FormData(e.target);
        const payload = Object.fromEntries(formData.entries());

        // --- THE SERIALIZER FIX ---
        payload.role = currentTargetRole;
        payload.parent_username = currentParentUsername;
        // Map 'match_comm_type' (HTML) to 'commission_type' (API)
        payload.commission_type = payload.match_comm_type === 'bet_by_bet' ? 'BET_BY_BET' : 'NO_COMMISSION';

        // Convert strings to numbers for the API
        ['coins', 'match_share', 'match_commission', 'session_commission', 'casino_share', 'casino_commission'].forEach(f => {
            payload[f] = parseFloat(payload[f]) || 0;
        });

        fetch("/api/create-user/", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            if (data.username || data.message) { alert("Success!"); location.reload(); }
            else { alert("Error: " + JSON.stringify(data)); }
        })
        .catch(err => alert("Network error"));
    });
});


// updated js for edit user
