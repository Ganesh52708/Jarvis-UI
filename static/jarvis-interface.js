// Global variables
let isReactorActive = false

// Initialize the interface when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  initializeInterface()
})

function initializeInterface() {
  // Create arc reactor segments
  createSegments()

  // Create energy arcs
  createEnergyArcs()

  // Create power indicators
  createPowerIndicators()

  // Start time updates
  updateTime()
  setInterval(updateTime, 1000)

  // Activate reactor after 500ms
  setTimeout(() => {
    activateReactor()
  }, 500)

  // Add click handler to reactor
  const reactor = document.getElementById("arcReactor")
  reactor.addEventListener("click", toggleReactor)
}

function createSegments() {
  // Create outer segments (60 segments)
  const outerSegments = document.getElementById("outerSegments")
  if (outerSegments) {
    for (let i = 0; i < 60; i++) {
      const segment = document.createElement("div")
      segment.className = "segment outer-segment"
      segment.style.transform = `translateX(-50%) rotate(${i * 6}deg)`
      segment.style.opacity = i % 5 === 0 ? 1 : 0.3
      outerSegments.appendChild(segment)
    }
  }

  // Create middle segments (40 segments)
  const middleSegments = document.getElementById("middleSegments")
  if (middleSegments) {
    for (let i = 0; i < 40; i++) {
      const segment = document.createElement("div")
      segment.className = "segment middle-segment"
      segment.style.transform = `translateX(-50%) rotate(${i * 9}deg)`
      segment.style.opacity = i % 3 === 0 ? 1 : 0.3
      middleSegments.appendChild(segment)
    }
  }

  // Create inner segments (24 segments)
  const innerSegments = document.getElementById("innerSegments")
  if (innerSegments) {
    for (let i = 0; i < 24; i++) {
      const segment = document.createElement("div")
      segment.className = "segment inner-segment"
      segment.style.transform = `translateX(-50%) rotate(${i * 15}deg)`
      segment.style.opacity = i % 2 === 0 ? 1 : 0.3
      innerSegments.appendChild(segment)
    }
  }
}

function createEnergyArcs() {
  const energyArcs = document.getElementById("energyArcs")
  if (energyArcs) {
    for (let i = 0; i < 8; i++) {
      const arc = document.createElement("div")
      arc.className = "energy-arc"
      arc.style.animationDelay = `${i * 0.5}s`
      energyArcs.appendChild(arc)
    }
  }
}

function createPowerIndicators() {
  const powerIndicators = document.getElementById("powerIndicators")
  if (powerIndicators) {
    for (let i = 0; i < 5; i++) {
      const bar = document.createElement("div")
      bar.className = "power-bar"
      bar.style.animationDelay = `${i * 200}ms`
      powerIndicators.appendChild(bar)
    }
  }
}

function updateTime() {
  const timeElement = document.getElementById("currentTime")
  if (timeElement) {
    const now = new Date()
    const timeString = now
      .toLocaleTimeString("en-US", {
        hour12: true,
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      })
      .replace(/:/g, " : ")

    timeElement.textContent = timeString
  }
}

function activateReactor() {
  isReactorActive = true
  const reactor = document.getElementById("arcReactor")
  if (reactor) {
    reactor.classList.add("active")
  }

  // Update status text
  const statusMain = document.getElementById("statusMain")
  const statusSub = document.getElementById("statusSub")
  if (statusMain) statusMain.textContent = "REACTOR ONLINE"
  if (statusSub) statusSub.textContent = "POWER: 100%"

  // Activate power bars
  const powerBars = document.querySelectorAll(".power-bar")
  powerBars.forEach((bar, index) => {
    if (index < 4) {
      setTimeout(() => {
        bar.classList.add("active")
      }, index * 200)
    }
  })
}

function deactivateReactor() {
  isReactorActive = false
  const reactor = document.getElementById("arcReactor")
  if (reactor) {
    reactor.classList.remove("active")
  }

  // Update status text
  const statusMain = document.getElementById("statusMain")
  const statusSub = document.getElementById("statusSub")
  if (statusMain) statusMain.textContent = "REACTOR OFFLINE"
  if (statusSub) statusSub.textContent = "POWER: 0%"

  // Deactivate power bars
  const powerBars = document.querySelectorAll(".power-bar")
  powerBars.forEach((bar) => {
    bar.classList.remove("active")
  })
}

function toggleReactor() {
  if (isReactorActive) {
    deactivateReactor()
  } else {
    activateReactor()
  }
}
