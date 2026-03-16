export function getDirectDriveLink(url) {
  if (!url ||!url.includes('drive.google.com')) return url;
  const match = url.match(/(?:id=|\[|\/d\/|\/file\/d\/)([\w-]{25,})/);
  return match? `https://drive.google.com/uc?export=view&id=${match[1]}` : url;
}
