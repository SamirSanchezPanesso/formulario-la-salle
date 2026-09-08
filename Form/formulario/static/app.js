const form = document.getElementById("contact-form")
const statusBox = document.getElementById("status")
const environmentBox = document.getElementById("environment")
const fields = ["name", "email", "subject", "message"]

async function loadEnvironment() {
    const response = await fetch("/api/environment")
    const data = await response.json()
    environmentBox.textContent = data.environment
}

function clearFeedback() {
    fields.forEach((field) => {
        document.getElementById(`${field}-error`).textContent = ""
    })
    statusBox.className = "status"
    statusBox.textContent = ""
}

function showErrors(errors) {
    Object.entries(errors || {}).forEach(([field, message]) => {
        const element = document.getElementById(`${field}-error`)
        if (element) element.textContent = message
    })
}

form.addEventListener("submit", async (event) => {
    event.preventDefault()
    clearFeedback()
    const button = form.querySelector("button")
    const payload = Object.fromEntries(new FormData(form).entries())
    button.disabled = true
    try {
        const response = await fetch("/api/contact", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload)
        })
        const data = await response.json()
        if (!response.ok) {
            showErrors(data.errors)
            statusBox.className = "status failure"
            statusBox.textContent = data.message
            return
        }
        statusBox.className = "status success"
        statusBox.textContent = data.message
        form.reset()
    } catch (error) {
        statusBox.className = "status failure"
        statusBox.textContent = "No fue posible procesar el formulario."
    } finally {
        button.disabled = false
    }
})

loadEnvironment()
