
// Auto-hide toast messages
window.addEventListener("DOMContentLoaded", () => {
  const toasts = document.querySelectorAll(".toast .msg");
  toasts.forEach((t, idx) => {
    setTimeout(() => {
      t.style.opacity = "0";
      t.style.transform = "translateY(-6px)";
      t.style.transition = "all .25s ease";
      setTimeout(()=> t.remove(), 300);
    }, 2200 + idx*150);
  });
});

// Confirm delete
function confirmDelete(msg){
  return confirm(msg || "Confermi l'eliminazione?");
}
