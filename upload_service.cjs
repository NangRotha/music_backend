/**
 * KhmerBeats Music Store - UploadThing Upload Service
 * Integrates UploadThing v7 UTApi for uploading images and media.
 */
const { UTApi } = require('uploadthing/server');
const fs = require('fs');
const path = require('path');

// Resolve UploadThing Token from environment
function getUploadThingToken() {
  if (process.env.UPLOADTHING_TOKEN && process.env.UPLOADTHING_TOKEN.trim()) {
    return process.env.UPLOADTHING_TOKEN.trim();
  }
  
  const secretKey = (process.env.UPLOADTHING_SECRET || '').trim();
  const appId = (process.env.UPLOADTHING_APP_ID || '').trim();
  
  if (secretKey && appId) {
    try {
      return Buffer.from(JSON.stringify({
        apiKey: secretKey,
        appId: appId,
        regions: ['sea1']
      })).toString('base64');
    } catch (e) {
      return '';
    }
  }
  return '';
}

async function main() {
  const filePath = process.argv[2];
  const originalName = process.argv[3] || 'upload.png';
  const mimeType = process.argv[4] || 'image/png';

  if (!filePath || !fs.existsSync(filePath)) {
    console.log(JSON.stringify({ success: false, error: 'File path not found: ' + filePath }));
    process.exit(1);
  }

  const token = getUploadThingToken();
  const utapi = new UTApi({ token });

  try {
    const buffer = fs.readFileSync(filePath);
    const file = new File([buffer], originalName, { type: mimeType });
    const response = await utapi.uploadFiles(file);

    if (response && response.data) {
      const data = response.data;
      const publicUrl = data.ufsUrl || data.url || data.appUrl;
      console.log(JSON.stringify({
        success: true,
        url: publicUrl,
        ufsUrl: data.ufsUrl,
        appUrl: data.appUrl,
        key: data.key,
        name: data.name,
        size: data.size,
        type: data.type
      }));
      process.exit(0);
    } else {
      console.log(JSON.stringify({
        success: false,
        error: response.error?.message || 'UploadThing returned no data'
      }));
      process.exit(1);
    }
  } catch (err) {
    console.log(JSON.stringify({
      success: false,
      error: err.message || String(err)
    }));
    process.exit(1);
  }
}

main();
