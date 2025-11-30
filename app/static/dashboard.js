// Cek apakah user sudah login
const token = localStorage.getItem('access_token');
if (!token) {
    window.location.href = '/login';
}

// Load user info
async function loadUserInfo() {
    try {
        const response = await fetch('/auth/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const user = await response.json();
            document.getElementById('userInfo').innerHTML = `
                <h3>Selamat datang, ${user.name}!</h3>
                <p><strong>Email:</strong> ${user.email}</p>
                <p><strong>Phone:</strong> ${user.phone || '-'}</p>
                <p><strong>User ID:</strong> ${user.id}</p>
            `;
            
            // Set user_id untuk form session
            window.currentUserId = user.id;
        } else {
            localStorage.removeItem('access_token');
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('Error loading user info:', error);
    }
}

// Load stations list
async function loadStations() {
    try {
        const response = await fetch('/stations');
        const stations = await response.json();
        
        const stationsList = document.getElementById('stationsList');
        
        if (stations.length === 0) {
            stationsList.innerHTML = '<p>Belum ada stasiun tersedia.</p>';
        } else {
            stationsList.innerHTML = stations.map(station => `
                <div class="station-item">
                    <h4>🏢 ${station.name}</h4>
                    <p>📍 ${station.location}</p>
                    <p><strong>ID:</strong> ${station.id}</p>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading stations:', error);
    }
}

// Start charging session
document.getElementById('startSessionForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const charger_unit_id = document.getElementById('charger_unit_id').value;
    const messageDiv = document.getElementById('message');
    
    try {
        const response = await fetch('/sessions', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: window.currentUserId,
                charger_unit_id: parseInt(charger_unit_id)
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            messageDiv.className = 'message success';
            messageDiv.textContent = `Session berhasil dimulai! Session ID: ${data.id}`;
            document.getElementById('startSessionForm').reset();
        } else {
            messageDiv.className = 'message error';
            messageDiv.textContent = data.detail || 'Gagal memulai session!';
        }
    } catch (error) {
        messageDiv.className = 'message error';
        messageDiv.textContent = 'Terjadi kesalahan: ' + error.message;
    }
});

// Logout
document.getElementById('logoutBtn').addEventListener('click', () => {
    localStorage.removeItem('access_token');
    window.location.href = '/login';
});

// Load data on page load
loadUserInfo();
loadStations();