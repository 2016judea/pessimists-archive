const fs=require('fs');const s=fs.readFileSync('main.js','utf8');
let idx=0,n=0;
while((idx=s.indexOf("JSON.parse('",idx))>=0){
  let j=idx+12, out='';
  while(true){ const c=s[j]; if(c==='\\'){j+=2;continue;} if(c==="'")break; j++; }
  const lit=s.slice(idx+11,j+1);
  const obj=JSON.parse(eval(lit));
  fs.writeFileSync(`blob${n}.json`,JSON.stringify(obj));
  console.log(n, lit.length, Array.isArray(obj)?'array '+obj.length:Object.keys(obj).slice(0,12).join(','));
  n++; idx=j;
}
