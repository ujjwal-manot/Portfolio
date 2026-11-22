// Parses ASCII and little-endian binary ngspice .raw waveform files in the browser into variable names and numeric arrays.
export interface RawWaveform {
  title: string;
  plotname: string;
  flags: string;
  variables: { index: number; name: string; unit: string }[];
  data: number[][];
}

export function parseNgspiceRaw(buffer: ArrayBuffer): RawWaveform {
  const bytes = new Uint8Array(buffer);
  const decoder = new TextDecoder("latin1");
  const fullText = decoder.decode(bytes);
  const binMarker = fullText.indexOf("\nBinary:\n");
  const binMarkerCr = fullText.indexOf("\r\nBinary:\r\n");
  const valMarker = fullText.indexOf("\nValues:\n");
  const valMarkerCr = fullText.indexOf("\r\nValues:\r\n");

  const isBinary = binMarker !== -1 || binMarkerCr !== -1;
  const headerEnd = isBinary
    ? binMarker !== -1
      ? binMarker
      : binMarkerCr
    : valMarker !== -1
      ? valMarker
      : valMarkerCr;
  if (headerEnd === -1) {
    throw new Error("invalid ngspice .raw file: missing Values or Binary section");
  }

  const headerText = fullText.slice(0, headerEnd);
  let title = "";
  let plotname = "";
  let flags = "";
  let numVars = 0;
  let numPoints = 0;
  const variables: { index: number; name: string; unit: string }[] = [];
  let inVars = false;

  for (const rawLine of headerText.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) continue;
    if (line.startsWith("Title:")) title = line.slice(6).trim();
    else if (line.startsWith("Plotname:")) plotname = line.slice(9).trim();
    else if (line.startsWith("Flags:")) flags = line.slice(6).trim();
    else if (line.startsWith("No. Variables:")) numVars = Number.parseInt(line.slice(14).trim(), 10);
    else if (line.startsWith("No. Points:")) numPoints = Number.parseInt(line.slice(11).trim(), 10);
    else if (line.startsWith("Variables:")) inVars = true;
    else if (inVars) {
      const parts = line.split(/\s+/);
      if (parts.length >= 3) {
        variables.push({ index: Number.parseInt(parts[0], 10), name: parts[1], unit: parts[2] });
      }
    }
  }

  if (numVars <= 0 || numPoints <= 0 || variables.length !== numVars) {
    throw new Error("invalid ngspice .raw header counts");
  }
  const isComplex = flags.toLowerCase().includes("complex");
  const data: number[][] = Array.from({ length: numVars }, () => new Array<number>(numPoints));

  if (isBinary) {
    const dataOffset = binMarker !== -1 ? binMarker + "\nBinary:\n".length : binMarkerCr + "\r\nBinary:\r\n".length;
    const view = new DataView(buffer, dataOffset);
    const stride = isComplex ? 16 : 8;
    let off = 0;
    for (let p = 0; p < numPoints; p++) {
      for (let v = 0; v < numVars; v++) {
        data[v][p] = view.getFloat64(off, true);
        off += stride;
      }
    }
  } else {
    const dataOffset = valMarker !== -1 ? valMarker + "\nValues:\n".length : valMarkerCr + "\r\nValues:\r\n".length;
    const body = fullText.slice(dataOffset);
    const tokens: string[] = [];
    for (const rawLine of body.split(/\r?\n/)) {
      const line = rawLine.trim();
      if (!line) continue;
      const parts = line.split(/\s+/);
      if (parts.length >= 2 && /^\d+$/.test(parts[0])) tokens.push(parts[1]);
      else tokens.push(parts[0]);
    }
    let idx = 0;
    for (let p = 0; p < numPoints; p++) {
      for (let v = 0; v < numVars; v++) {
        const tok = tokens[idx++] ?? "0";
        data[v][p] = Number.parseFloat(tok.split(",")[0]);
      }
    }
  }

  return { title, plotname, flags, variables, data };
}
