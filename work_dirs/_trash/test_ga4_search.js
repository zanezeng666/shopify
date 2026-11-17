(async()=>{
  await new Promise(r=>setTimeout(r,3000));
  window.__evts=[];
  window.gtag=function(){window.__evts.push(JSON.stringify([...arguments].slice(0,2)));};
  const q=document.getElementById('ebs-q')||document.querySelector('input[type=search],input.ebs-q');
  if(!q)return 'NO_INPUT:'+document.querySelectorAll('input').length;
  q.value='DW01';
  q.dispatchEvent(new Event('input',{bubbles:true}));
  await new Promise(r=>setTimeout(r,900));
  return 'EVTS='+JSON.stringify(window.__evts)+' count='+document.getElementById('ebs-count').textContent;
})()
