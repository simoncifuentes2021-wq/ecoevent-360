const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const logisticsRoot = path.join(__dirname, "..", "components", "logistics");
const read = (name) => fs.readFileSync(path.join(logisticsRoot, name), "utf8");

test("las evidencias logisticas cargan archivos privados con autenticacion", () => {
  const uploader = read("LogisticsEvidenceUploader.tsx");
  const gallery = read("LogisticsEvidenceGallery.tsx");
  const preview = read("LogisticsEvidencePreviewModal.tsx");
  const thumbnail = read("LogisticsEvidenceThumbnail.tsx");

  assert.match(uploader, /LogisticsEvidenceThumbnail/);
  assert.match(gallery, /LogisticsEvidenceThumbnail/);
  assert.match(preview, /usePrivateFileUrl\(evidence\.file_url\)/);
  assert.match(thumbnail, /usePrivateFileUrl\(evidence\.file_url\)/);

  for (const source of [uploader, gallery, preview]) {
    assert.doesNotMatch(source, /fileUrl\(item\.file_url\)|fileUrl\(evidence\.file_url\)/);
  }
});
