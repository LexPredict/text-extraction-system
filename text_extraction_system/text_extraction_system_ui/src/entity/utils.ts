export function formatDatetime (m: Date): string {
    return m.getUTCFullYear() + "/" + 
      (m.getUTCMonth()+1) + "/" + 
      m.getUTCDate() + " " + 
      pad(m.getUTCHours(), 2) + ":" + pad(m.getUTCMinutes(), 2) + ":" + pad(m.getUTCSeconds(), 2);
}

function pad(num, size) {
  const s = "000000000" + num;
  return s.substr(s.length-size);
}