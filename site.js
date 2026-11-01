const root = document.documentElement;
root.dataset.theme = localStorage.getItem("theme") || "dark";
document.getElementById("theme").onclick = () => {
  root.dataset.theme = root.dataset.theme === "light" ? "dark" : "light";
  localStorage.setItem("theme", root.dataset.theme);
};

const nav = document.querySelector("nav");
const menu = document.getElementById("menu");
menu.onclick = () => {
  const open = nav.classList.toggle("open");
  menu.setAttribute("aria-expanded", String(open));
  menu.textContent = open ? "Close" : "Menu";
};
document.querySelectorAll("#nav-links a").forEach(link => {
  link.addEventListener("click", () => {
    nav.classList.remove("open");
    menu.setAttribute("aria-expanded", "false");
    menu.textContent = "Menu";
  });
});

const chips = document.querySelectorAll(".chip"), cards = document.querySelectorAll(".card");
chips.forEach(c => c.onclick = () => {
  chips.forEach(x => x.classList.toggle("on", x === c));
  const lens = c.dataset.lens;
  cards.forEach(k => k.classList.toggle("dim", lens !== "all" && !k.dataset.tags.includes(lens)));
});

document.querySelectorAll('a[href^="http"]').forEach(link => {
  link.target = "_blank";
  link.rel = "noopener noreferrer";
});

document.getElementById("year").textContent = new Date().getFullYear();
