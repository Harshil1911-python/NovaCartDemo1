/* Nova Cart - Admin JS */

document.addEventListener('DOMContentLoaded', function () {
  // Sidebar toggle (mobile)
  const toggleBtns = document.querySelectorAll('.sidebar-toggle');
  toggleBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      document.getElementById('adminSidebar')?.classList.toggle('open');
      document.getElementById('sellerSidebar')?.classList.toggle('open');
    });
  });

  // Auto dismiss flash
  document.querySelectorAll('.flash').forEach(f => setTimeout(() => f.remove(), 5000));

  // Confirm deletes
  document.querySelectorAll('form[onsubmit]').forEach(f => {
    // already handled inline
  });

  // Image preview on file input
  document.querySelectorAll('input[type="file"]').forEach(input => {
    input.addEventListener('change', function () {
      const files = Array.from(this.files);
      const container = this.parentElement;
      let preview = container.querySelector('.file-preview');
      if (!preview) {
        preview = document.createElement('div');
        preview.className = 'file-preview';
        preview.style.cssText = 'display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.5rem';
        container.appendChild(preview);
      }
      preview.innerHTML = '';
      files.forEach(file => {
        if (!file.type.startsWith('image/')) return;
        const reader = new FileReader();
        reader.onload = e => {
          const img = document.createElement('img');
          img.src = e.target.result;
          img.style.cssText = 'width:70px;height:70px;object-fit:cover;border-radius:8px;border:2px solid #E2E8F0';
          preview.appendChild(img);
        };
        reader.readAsDataURL(file);
      });
    });
  });

  // Color input sync
  document.querySelectorAll('input[type="color"]').forEach(cp => {
    const textId = 'ct_' + cp.name;
    const textInput = document.getElementById(textId);
    if (textInput) {
      cp.addEventListener('input', () => textInput.value = cp.value);
      textInput.addEventListener('input', () => {
        if (/^#[0-9A-Fa-f]{6}$/.test(textInput.value)) cp.value = textInput.value;
      });
    }
  });
});

// CSRF helper for admin
function getCsrf() {
  const inp = document.querySelector('input[name="csrf_token"]');
  return inp ? inp.value : '';
}
