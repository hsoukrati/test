"use strict";

/*

* OCR PLATFORM
* Frontend OCR uniquement
* Sans IA / Sans LLM
  */

const API_BASE = "http://127.0.0.1:5000";

let selectedFile = null;
let currentResult = null;

// ============================================================
// ELEMENTS
// ============================================================

const fileInput = document.getElementById("fileInput");
const selectFileBtn = document.getElementById("selectFileBtn");
const dropZone = document.getElementById("dropZone");

const selectedFileBox = document.getElementById("selectedFile");
const fileName = document.getElementById("fileName");
const fileSize = document.getElementById("fileSize");

const removeFileBtn = document.getElementById("removeFileBtn");
const extractBtn = document.getElementById("extractBtn");

const progressCard = document.getElementById("progressCard");
const progressBar = document.getElementById("progressBar");
const progressText = document.getElementById("progressText");
const progressMessage = document.getElementById("progressMessage");

const errorCard = document.getElementById("errorCard");
const errorMessage = document.getElementById("errorMessage");

const resultsSection = document.getElementById("resultsSection");

const apiDot = document.getElementById("apiDot");
const apiStatus = document.getElementById("apiStatus");

const downloadBtn = document.getElementById("downloadBtn");

// ============================================================
// INITIALISATION
// ============================================================

document.addEventListener("DOMContentLoaded", () => {
setupFileEvents();
setupDownload();
checkAPI();
});

// ============================================================
// VERIFICATION API
// ============================================================

async function checkAPI() {
try {
const response = await fetch(`${API_BASE}/api/health`);


    if (!response.ok) {
        throw new Error("API indisponible");
    }

    const data = await response.json();

    if (data.success && data.ocr_enabled) {
        if (apiDot) {
            apiDot.classList.remove("offline");
            apiDot.classList.add("online");
        }

        if (apiStatus) {
            apiStatus.textContent = "API OCR connectée";
        }
    } else {
        setAPIOffline("OCR indisponible");
    }
} catch (error) {
    console.error("Erreur API :", error);
    setAPIOffline("API hors ligne");
}


}

function setAPIOffline(message) {
if (apiDot) {
apiDot.classList.remove("online");
apiDot.classList.add("offline");
}


if (apiStatus) {
    apiStatus.textContent = message;
}


}

// ============================================================
// EVENTS FICHIER
// ============================================================

function setupFileEvents() {
if (!fileInput || !dropZone) {
console.error("Éléments fichier introuvables dans index.html");
return;
}


if (selectFileBtn) {
    selectFileBtn.addEventListener("click", (event) => {
        event.stopPropagation();
        fileInput.click();
    });
}

dropZone.addEventListener("click", () => {
    fileInput.click();
});

fileInput.addEventListener("change", (event) => {
    const file = event.target.files?.[0];

    if (file) {
        selectFile(file);
    }
});

dropZone.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropZone.classList.add("dragging");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragging");
});

dropZone.addEventListener("drop", (event) => {
    event.preventDefault();

    dropZone.classList.remove("dragging");

    const file = event.dataTransfer.files?.[0];

    if (file) {
        selectFile(file);
    }
});

if (removeFileBtn) {
    removeFileBtn.addEventListener("click", clearFile);
}

if (extractBtn) {
    extractBtn.addEventListener("click", processDocument);
}


}

// ============================================================
// SELECTION FICHIER
// ============================================================

function selectFile(file) {
const allowedExtensions = [
"pdf",
"png",
"jpg",
"jpeg",
"tif",
"tiff",
"bmp"
];


const extension = file.name
    .split(".")
    .pop()
    .toLowerCase();

if (!allowedExtensions.includes(extension)) {
    showError(
        "Format non supporté. Utilisez PDF, PNG, JPG, JPEG, TIFF ou BMP."
    );

    return;
}

selectedFile = file;
currentResult = null;

if (fileName) {
    fileName.textContent = file.name;
}

if (fileSize) {
    fileSize.textContent = formatFileSize(file.size);
}

if (selectedFileBox) {
    selectedFileBox.classList.remove("hidden");
}

if (extractBtn) {
    extractBtn.disabled = false;
}

if (resultsSection) {
    resultsSection.classList.add("hidden");
}

hideError();


}

// ============================================================
// SUPPRIMER FICHIER
// ============================================================

function clearFile() {
selectedFile = null;
currentResult = null;


if (fileInput) {
    fileInput.value = "";
}

if (selectedFileBox) {
    selectedFileBox.classList.add("hidden");
}

if (extractBtn) {
    extractBtn.disabled = true;
}

if (resultsSection) {
    resultsSection.classList.add("hidden");
}

hideError();


}

// ============================================================
// EXTRACTION OCR
// ============================================================

async function processDocument() {
if (!selectedFile) {
showError("Veuillez sélectionner un document.");
return;
}


hideError();

if (resultsSection) {
    resultsSection.classList.add("hidden");
}

if (extractBtn) {
    extractBtn.disabled = true;
}

if (progressCard) {
    progressCard.classList.remove("hidden");
}

try {
    // ----------------------------------------------------
    // 1. UPLOAD
    // ----------------------------------------------------

    updateProgress(
        10,
        "Envoi du document..."
    );

    const formData = new FormData();

    formData.append("file", selectedFile);

    const uploadResponse = await fetch(
        `${API_BASE}/api/upload/file`,
        {
            method: "POST",
            body: formData
        }
    );

    const uploadData = await parseResponse(uploadResponse);

    if (
        !uploadResponse.ok ||
        uploadData.success === false
    ) {
        throw new Error(
            uploadData.message ||
            uploadData.error ||
            "Erreur pendant l'upload."
        );
    }

    updateProgress(
        35,
        "Document envoyé. Préparation de l'OCR..."
    );

    // ----------------------------------------------------
    // 2. NOM DU FICHIER
    // ----------------------------------------------------

    const filename =
        uploadData.filename ||
        uploadData.document?.filename ||
        selectedFile.name;

    // ----------------------------------------------------
    // 3. EXTRACTION OCR
    // ----------------------------------------------------

    updateProgress(
        50,
        "Extraction OCR en cours..."
    );

    const extractionResponse = await fetch(
        `${API_BASE}/api/extraction/run`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                filename: filename
            })
        }
    );

    const extractionData =
        await parseResponse(extractionResponse);

    if (
        !extractionResponse.ok ||
        extractionData.success === false
    ) {
        throw new Error(
            extractionData.message ||
            extractionData.error ||
            "Erreur pendant l'extraction OCR."
        );
    }

    updateProgress(
        85,
        "Traitement des champs et tableaux..."
    );

    // ----------------------------------------------------
    // 4. RESULTAT
    // ----------------------------------------------------

    currentResult =
        extractionData.result ||
        extractionData.data ||
        extractionData;

    updateProgress(
        100,
        "Extraction terminée."
    );

    await sleep(400);

    if (progressCard) {
        progressCard.classList.add("hidden");
    }

    displayResults(currentResult);

} catch (error) {
    console.error(
        "Erreur extraction :",
        error
    );

    if (progressCard) {
        progressCard.classList.add("hidden");
    }

    showError(
        error.message ||
        "Une erreur est survenue pendant l'extraction."
    );

} finally {
    if (extractBtn) {
        extractBtn.disabled = false;
    }
}


}

// ============================================================
// AFFICHAGE RESULTATS
// ============================================================

function displayResults(result) {
if (!result) {
showError("Aucun résultat OCR reçu.");
return;
}


if (resultsSection) {
    resultsSection.classList.remove("hidden");
}

const documentInfo =
    result.document || {};

const fields =
    result.fields || {};

const tables =
    Array.isArray(result.tables)
        ? result.tables
        : [];

const text =
    result.text ||
    result.full_text ||
    "";

const confidenceValue =
    result.confidence ??
    result.global_confidence ??
    0;

const confidence =
    Number(confidenceValue) || 0;

// --------------------------------------------------------
// DOCUMENT
// --------------------------------------------------------

const resultFilename =
    document.getElementById("resultFilename");

if (resultFilename) {
    resultFilename.textContent =
        documentInfo.filename ||
        selectedFile?.name ||
        "Document";
}

// --------------------------------------------------------
// STATISTIQUES
// --------------------------------------------------------

const fieldsCount =
    document.getElementById("fieldsCount");

if (fieldsCount) {
    fieldsCount.textContent =
        Object.keys(fields).length;
}

const tablesCount =
    document.getElementById("tablesCount");

if (tablesCount) {
    tablesCount.textContent =
        tables.length;
}

const pagesCount =
    document.getElementById("pagesCount");

if (pagesCount) {
    pagesCount.textContent =
        documentInfo.pages || 0;
}

const confidenceElement =
    document.getElementById("confidenceValue");

if (confidenceElement) {
    confidenceElement.textContent =
        formatConfidence(confidence);
}

// --------------------------------------------------------
// CHAMPS
// --------------------------------------------------------

renderFields(fields);

// --------------------------------------------------------
// TABLEAUX
// --------------------------------------------------------

renderTables(tables);

// --------------------------------------------------------
// TEXTE OCR
// --------------------------------------------------------

const ocrText =
    document.getElementById("ocrText");

if (ocrText) {
    ocrText.textContent = text;
}

// --------------------------------------------------------
// SCROLL
// --------------------------------------------------------

if (resultsSection) {
    resultsSection.scrollIntoView({
        behavior: "smooth"
    });
}


}

// ============================================================
// CHAMPS
// ============================================================

function renderFields(fields) {
const container =
document.getElementById("fieldsContainer");


if (!container) {
    return;
}

container.innerHTML = "";

const entries =
    Object.entries(fields);

if (entries.length === 0) {
    container.innerHTML =
        `<div class="empty-state">
            Aucun champ détecté.
        </div>`;

    return;
}

entries.forEach(([key, value]) => {
    const field =
        document.createElement("div");

    field.className = "field";

    const label =
        document.createElement("span");

    label.className = "field-label";

    label.textContent =
        formatLabel(key);

    const valueElement =
        document.createElement("div");

    valueElement.className =
        "field-value";

    valueElement.textContent =
        formatValue(value);

    field.appendChild(label);
    field.appendChild(valueElement);

    container.appendChild(field);
});


}

// ============================================================
// TABLEAUX
// ============================================================

function renderTables(tables) {
const container =
document.getElementById("tablesContainer");


if (!container) {
    return;
}

container.innerHTML = "";

if (!tables.length) {
    container.innerHTML =
        `<div class="empty-state">
            Aucun tableau détecté.
        </div>`;

    return;
}

tables.forEach((table, index) => {
    const wrapper =
        document.createElement("div");

    wrapper.className =
        "table-wrapper";

    const title =
        document.createElement("h4");

    title.textContent =
        `Tableau ${index + 1}`;

    wrapper.appendChild(title);

    const tableElement =
        document.createElement("table");

    const rows =
        Array.isArray(table)
            ? table
            : Array.isArray(table.rows)
                ? table.rows
                : [];

    if (!rows.length) {
        const empty =
            document.createElement("div");

        empty.className =
            "empty-state";

        empty.textContent =
            "Tableau vide";

        wrapper.appendChild(empty);

        container.appendChild(wrapper);

        return;
    }

    rows.forEach((row, rowIndex) => {
        const tr =
            document.createElement("tr");

        const values =
            Array.isArray(row)
                ? row
                : Object.values(row);

        values.forEach((value) => {
            const cell =
                document.createElement(
                    rowIndex === 0
                        ? "th"
                        : "td"
                );

            cell.textContent =
                formatValue(value);

            tr.appendChild(cell);
        });

        tableElement.appendChild(tr);
    });

    wrapper.appendChild(tableElement);

    container.appendChild(wrapper);
});


}

// ============================================================
// TELECHARGEMENT JSON
// ============================================================

function setupDownload() {
if (!downloadBtn) {
return;
}


downloadBtn.addEventListener(
    "click",
    downloadJSON
);


}

function downloadJSON() {
if (!currentResult) {
showError(
"Aucun résultat disponible à télécharger."
);


    return;
}

const blob =
    new Blob(
        [
            JSON.stringify(
                currentResult,
                null,
                2
            )
        ],
        {
            type: "application/json"
        }
    );

const url =
    URL.createObjectURL(blob);

const link =
    document.createElement("a");

link.href = url;

const originalName =
    selectedFile?.name ||
    "resultat";

const baseName =
    originalName.replace(
        /\.[^/.]+$/,
        ""
    );

link.download =
    `${baseName}_ocr.json`;

document.body.appendChild(link);

link.click();

link.remove();

URL.revokeObjectURL(url);


}

// ============================================================
// PROGRESSION
// ============================================================

function updateProgress(percent, message) {
if (progressBar) {
progressBar.style.width =
`${percent}%`;
}


if (progressText) {
    progressText.textContent =
        `${percent}%`;
}

if (progressMessage) {
    progressMessage.textContent =
        message;
}


}

// ============================================================
// ERREURS
// ============================================================

function showError(message) {
if (errorMessage) {
errorMessage.textContent =
message;
}


if (errorCard) {
    errorCard.classList.remove("hidden");
}


}

function hideError() {
if (errorCard) {
errorCard.classList.add("hidden");
}
}

// ============================================================
// UTILITAIRES
// ============================================================

async function parseResponse(response) {
const text =
await response.text();


if (!text) {
    throw new Error(
        `Réponse API vide (${response.status}).`
    );
}

try {
    return JSON.parse(text);

} catch (error) {
    console.error(
        "Réponse API non JSON :",
        text
    );

    throw new Error(
        `Réponse API invalide (${response.status}).`
    );
}


}

function formatFileSize(bytes) {
if (bytes < 1024) {
return `${bytes} B`;
}


if (bytes < 1024 * 1024) {
    return `${(
        bytes / 1024
    ).toFixed(1)} KB`;
}

return `${(
    bytes / (1024 * 1024)
).toFixed(1)} MB`;


}

function formatConfidence(value) {
let confidence =
Number(value) || 0;


if (confidence <= 1) {
    confidence *= 100;
}

confidence =
    Math.max(
        0,
        Math.min(
            100,
            confidence
        )
    );

return `${Math.round(confidence)}%`;


}

function formatLabel(value) {
return String(value)
.replaceAll("_", " ")
.replace(
/\b\w/g,
(char) => char.toUpperCase()
);
}

function formatValue(value) {
if (
value === null ||
value === undefined
) {
return "";
}


if (
    typeof value === "object"
) {
    return JSON.stringify(value);
}

return String(value);


}

function sleep(ms) {
return new Promise(
(resolve) =>
setTimeout(resolve, ms)
);
}
