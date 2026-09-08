const API_URL = "https://formulario-la-salle.onrender.com"

const form = document.getElementById("contact-form")
const statusBox = document.getElementById("status")
const environmentBox = document.getElementById("environment")
const fields = ["name", "email", "subject", "message"]

async function loadEnvironment() {
    try {
        const response = await fetch(`${API_URL}/api/environment`)

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`)
        }

        const data = await response.json()
        environmentBox.textContent = data.environment
    } catch (error) {
        console.error(error)
        environmentBox.textContent = "No disponible"
    }
}

function clearFeedback() {
    fields.forEach((field) => {
        const element = document.getElementById(`${field}-error`)
        if (element) {
            element.textContent = ""
        }
    })

    statusBox.className = "status"
    statusBox.textContent = ""
}

function showErrors(errors) {
    Object.entries(errors || {}).forEach(([field, message]) => {
        const element = document.getElementById(`${field}-error`)

        if (element) {
            element.textContent = message
        }
    })
}

form.addEventListener("submit", async (event) => {
    event.preventDefault()

    clearFeedback()

    const button = form.querySelector("button")
    const payload = Object.fromEntries(new FormData(form).entries())

    button.disabled = true
    button.textContent = "Enviando..."

    try {
        const response = await fetch(`${API_URL}/api/contact`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        })

        const data = await response.json()

        if (!response.ok) {
            showErrors(data.errors)

            statusBox.className = "status failure"
            statusBox.textContent =
                data.message || "No fue posible procesar el formulario."

            return
        }

        statusBox.className = "status success"
        statusBox.textContent =
            data.message || "Tu mensaje fue enviado correctamente."

        form.reset()
    } catch (error) {
        console.error(error)

        statusBox.className = "status failure"
        statusBox.textContent =
            "No fue posible conectar con el servidor."
    } finally {
        button.disabled = false
        button.textContent = "Enviar mensaje"
    }
})

loadEnvironment()
