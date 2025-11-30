document.getElementById('registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const name = document.getElementById('name').value;
    const email = document.getElementById('email').value;
    const phone = document.getElementById('phone').value;
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirm_password').value;
    const messageDiv = document.getElementById('message');
    
    // Validasi password
    if (password !== confirmPassword) {
        messageDiv.className = 'message error';
        messageDiv.textContent = 'Password tidak cocok!';
        return;
    }
    
    if (password.length < 6) {
        messageDiv.className = 'message error';
        messageDiv.textContent = 'Password minimal 6 karakter!';
        return;
    }
    
    try {
        const response = await fetch('/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name, email, phone, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            messageDiv.className = 'message success';
            messageDiv.textContent = 'Registrasi berhasil! Mengalihkan ke halaman login...';
            
            // Redirect ke login
            setTimeout(() => {
                window.location.href = '/login';
            }, 2000);
        } else {
            messageDiv.className = 'message error';
            messageDiv.textContent = data.detail || 'Registrasi gagal!';
        }
    } catch (error) {
        messageDiv.className = 'message error';
        messageDiv.textContent = 'Terjadi kesalahan: ' + error.message;
    }
});