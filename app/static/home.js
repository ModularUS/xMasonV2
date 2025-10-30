
const thickness_field = document.getElementById("thickness_text")
const material_selector = document.getElementById("material_selector")
const unit_selector = document.getElementById("unit_selector")
const cross_section_label = document.getElementById("cross_section_label")
const transducer_stack = document.getElementById("transducer_stack")
const add_layer_button = document.getElementById("add_layer_button")
const run_simulation_button = document.getElementById("run_simulation_button")
const right_column = document.getElementById("rightcolumn")
const cross_section_field = document.getElementById("cross_section_field")
const start_freq_field = document.getElementById("start_freq_field")
const stop_freq_field = document.getElementById("stop_freq_field")

add_layer_button.onclick = addLayerPressed
run_simulation_button.onclick = runSimulationPressed

const layer_stack = []
const del_to_layer = new Map()
const pol_to_layer = new Map()

material_registry = []

async function sendData(type, data)
{
    let response = await fetch("/post", {
    method: "POST",
    body: JSON.stringify(data),
    headers: {
       "Content-type": "application/json",
       "Type": type
    }
    })
    if(!response.ok) alert("Cannot communicate with server")
    return response
}

async function getData(type)
{
    let response = await fetch("/get", {
       "headers": {
           "Content-Type": "application/json",
           "Type": type
       }
    })
   if(!response.ok)
   {
       alert("Cannot comunicate with server")
       return null
   }
   return await response.json()
}

function getConnectionPick()
{
    return document.querySelector('input[name="connection"]:checked').value
}

function getCrossSectionPick()
{
    return document.querySelector('input[name="cross_section"]:checked').value
}

function bodyLoaded()
{
    populateMaterials()
    populateDefaultStack()
}

// Request materials from server, fill material registry and material selector
async function populateMaterials()
{
    let data = (await getData("materials"))
    let materials = data["materials"]
    let isPiezo = data["isPiezo"]
    for(let i = 0; i < materials.length; i++)
    {
        let m = materials[i]
        let op = document.createElement("option")
        op.value = m
        op.textContent = m
        material_selector.appendChild(op)
        material_registry[m] = isPiezo[i]
    }
}

// Fill the stack with some default setup defined on server
async function populateDefaultStack()
{
    let stack = (await getData("default_stack"))
    if(stack === null) return
    let materials = stack["materials"]
    let thickness = stack["thickness"]
    let polarization = stack["polarization"]
    for(let i = 0; i < materials.length; i++)
        addLayer(materials[i],thickness[i],"um", polarization[i])
}

function addLayerPressed()
{
    //Preliminary input validation, finalized on server
    let material = material_selector.value
    if(material === "")
    {
        alert("No material selected")
        return
    }
    let thickness = parseFloat(thickness_field.value)
    if(isNaN(thickness))
    {
        alert("No thickness specified")
        return
    }
    let unit = unit_selector.value
    addLayer(material, thickness, unit, false)
}

function deleteLayerPressed(event)
{
    removeLayer(del_to_layer.get(event.target))
}

function polarizationPressed(event)
{
    let layer = pol_to_layer.get(event.target)
    let pol = layer.polarization
    //Upward polarization
    if(pol)
    {
        layer.polarization = false
        layer.polarization_button.value = "↓"
    }
    //Downward polarization
    else
    {
        layer.polarization = true
        layer.polarization_button.value = "↑"
    }
}

function crossSectionPressed(event)
{
    let shape = getCrossSectionPick()
    if(shape === "circle") cross_section_label.innerHTML = "Diameter [mm]:"
    else if(shape === "square") cross_section_label.innerHTML = "Side length [mm]:"
    else cross_section_label.innerHTML = "Area [mm^2]:"
}

function runSimulationPressed()
{
    let stack_json = {}
    stack_json["materials"] = []
    stack_json["thickness"] = []
    stack_json["polarization"] = []
    stack_json["connection"] = getConnectionPick()
    let cross_section_pick = getCrossSectionPick()
    let cross_section_value = cross_section_field.value
    if(cross_section_pick === "circle")
        stack_json["area"] = (cross_section_value * 1E-3 / 2.0)**2 * Math.PI
    else if(cross_section_pick === "square")
        stack_json["area"] = (cross_section_value * 1E-3)**2
    else stack_json["area"] = cross_section_value * 1E-6

    // Add frequency band
    let start_freq = parseFloat(start_freq_field.value)
    let stop_freq = parseFloat(stop_freq_field.value)
    if(isNaN(start_freq) || start_freq < 0)
    {
        alert("Invalid start frequency")
        return
    }
    if(isNaN(stop_freq) || stop_freq <= 0)
    {
        alert("Invalid stop frequency")
        return
    }
    if(start_freq >= stop_freq)
    {
        alert("Start frequency must be less than stop frequency")
        return
    }
    stack_json["start_freq"] = start_freq
    stack_json["stop_freq"] = stop_freq

    for(let l of layer_stack)
    {
        stack_json["materials"].push(l.material)
        stack_json["thickness"].push(l.thickness)
        stack_json["polarization"].push(l.polarization)
    }
    sendData("simulation_scripts", stack_json).then((response) => {
        if(response.ok) response.blob().then((blob) => {
            // Remove existing image if present
            let existingImg = document.getElementById("result_image")
            if(existingImg) existingImg.remove()

            // Create and add new image
            let img = new Image()
            img.src = URL.createObjectURL(blob)
            img.id = "result_image"
            right_column.appendChild(img)
        })})
}

function addLayer(material, thickness, unit, polarization)
{
    let layer = {}

    layer.material = material
    let factor = 1
    if(unit === "mm") factor = 1E-3
    else if(unit === "um")
    {
        factor = 1E-6
        unit = "μm"
    }

    else if(unit === "nm") factor = 1E-9
    layer.thickness = thickness * factor
    layer.polarization = polarization

    let layer_div = document.createElement("div")
    layer_div.classList.add("layer_label")
    layer_div.innerHTML = material + " " + thickness + " " + unit
    transducer_stack.appendChild(layer_div)
    layer.layer_div = layer_div

    let del_button = document.createElement("input")
    del_button.type = "button"
    del_button.classList.add("dark_button")
    del_button.style.height = "32px"
    del_button.style.width = "32px"
    del_button.style.fontStyle = "25px"
    del_button.classList.add("remove_button")
    del_button.value = "X"
    del_button.addEventListener("click", deleteLayerPressed)
    transducer_stack.appendChild(del_button)
    layer.delete_button = del_button
    del_to_layer.set(del_button, layer)

    //if is piezo
    if(material_registry[material])
    {
        let pol_button = document.createElement("input")
        pol_button.type = "button"
        pol_button.classList.add("dark_button")
        pol_button.style.height = "24px"
        pol_button.style.width = "24px"
        pol_button.style.marginLeft = "4px";
        pol_button.style.fontStyle = "20px"
        pol_button.value = polarization ? "↑" : "↓"
        pol_button.addEventListener("click", polarizationPressed)
        layer_div.appendChild(pol_button)
        layer.polarization_button = pol_button
        pol_to_layer.set(pol_button, layer)
    }
    else layer.polarization_button = null

    layer_stack.push(layer)
}

function removeLayer(layer)
{
    if(layer.polarization_button != null)
    {
        pol_to_layer.delete(layer.polarization_button)
        layer.polarization_button.remove()
    }
    del_to_layer.delete(layer.delete_button)
    layer.delete_button.remove()
    layer.layer_div.remove()

    layer_stack.splice(layer_stack.indexOf(layer), 1)
}