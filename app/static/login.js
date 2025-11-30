document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const messageDiv = document.getElementById('message');
    
    try {
        const response = await fetch('/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Simpan token ke localStorage
            localStorage.setItem('access_token', data.access_token);
            
            // Tampilkan pesan sukses
            messageDiv.className = 'message success';
            messageDiv.textContent = 'Login berhasil! Mengalihkan ke dashboard...';
            
            // Redirect ke dashboard
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1000);
        } else {
            messageDiv.className = 'message error';
            messageDiv.textContent = data.detail || 'Login gagal!';
        }
    } catch (error) {
        messageDiv.className = 'message error';
        messageDiv.textContent = 'Terjadi kesalahan: ' + error.message;
    }
});