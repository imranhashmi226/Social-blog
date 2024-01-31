const signInBtn = document.getElementById("signIn");
const signUpBtn = document.getElementById("signUp");
const fistForm = document.getElementById("form1");
const secondForm = document.getElementById("form2");
const thirdForm = document.getElementById("form3");
const fourForm = document.getElementById("form4");
const container = document.querySelector(".container");

// const swup = new Swup()

signInBtn.addEventListener("click", () => {
	container.classList.remove("right-panel-active");
});

signUpBtn.addEventListener("click", () => {
	container.classList.add("right-panel-active");
});

fistForm.addEventListener("submit", (e) => e.preventDefault());
secondForm.addEventListener("submit", (e) => e.preventDefault());
thirdForm.addEventListener("submit", (e) => e.preventDefault());
fourForm.addEventListener("submit", (e) => e.preventDefault());