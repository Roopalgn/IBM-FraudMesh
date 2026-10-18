// Presentation only: no transaction generation, detector timing, or model changes.
export const MOTION = Object.freeze({reveal:780, inspector:420, view:260, feedback:180});
const EASE = 'cubic-bezier(.16,1,.3,1)';

export function frameSummary(intervals) {
  const values=intervals.filter(n=>Number.isFinite(n)&&n>0).sort((a,b)=>a-b);
  if(!values.length)return null;
  const at=q=>Number(values[Math.min(values.length-1,Math.ceil(values.length*q)-1)].toFixed(2));
  return {frames:values.length,p50_ms:at(.5),p95_ms:at(.95),max_ms:at(1)};
}

export function createMotionSystem() {
  const body=document.body,media=matchMedia('(prefers-reduced-motion: reduce)');
  const running=new Map();
  let enabled=!media.matches,sceneInViewport=true,view='network',sceneTimer,profileFrame;
  function sync(){
    body.classList.toggle('motion-reduced',!enabled);
    body.classList.toggle('motion-paused',document.hidden);
    body.classList.toggle('scene-offscreen',!sceneInViewport||view!=='network');
    const button=document.getElementById('motion-toggle');
    button?.setAttribute('aria-pressed',String(enabled));
    if(button){button.querySelector('span:last-child').textContent=enabled?'Motion on':'Motion off';button.disabled=media.matches;button.title=media.matches?'System reduced-motion preference is active':'Toggle interface motion';}
    if(!enabled||document.hidden){for(const a of running.values())a.cancel();running.clear();cancelAnimationFrame(profileFrame);}
  }
  function animate(element,frames,options={}){
    if(!element||!enabled||document.hidden||typeof element.animate!=='function')return;
    running.get(element)?.cancel();
    const animation=element.animate(frames,{duration:MOTION.view,easing:EASE,...options});
    running.set(element,animation);
    animation.finished.then(()=>{if(running.get(element)===animation)running.delete(element);}).catch(()=>{});
    return animation;
  }
  function panel(element,delay=0){return animate(element,[{opacity:.4,transform:'translateY(10px)'},{opacity:1,transform:'translateY(0)'}],{duration:MOTION.inspector,delay});}
  function capture(){
    return new Map(Array.from(document.querySelectorAll('#graph .node')).map(n=>{
      const c=n.querySelector('circle');return [n.dataset.node,[Number(c.getAttribute('cx')),Number(c.getAttribute('cy'))]];
    }));
  }
  function profile(){
    if(!new URLSearchParams(location.search).has('profile'))return;
    delete body.dataset.motionProfile;
    cancelAnimationFrame(profileFrame);
    const intervals=[];let first,last;
    const sample=now=>{
      first??=now;if(last!=null)intervals.push(now-last);last=now;
      if(document.hidden)return;
      if(now-first<1100)profileFrame=requestAnimationFrame(sample);
      else body.dataset.motionProfile=JSON.stringify({...frameSummary(intervals),scope:'one local browser reveal; not inference latency'});
    };
    profileFrame=requestAnimationFrame(sample);
  }
  function reveal(previous=new Map()){
    const scene=document.querySelector('.network-panel');
    clearTimeout(sceneTimer);scene.classList.remove('entering');
    if(!enabled||document.hidden)return;
    void scene.offsetWidth;scene.classList.add('entering');
    sceneTimer=setTimeout(()=>scene.classList.remove('entering'),MOTION.reveal+140);
    for(const node of document.querySelectorAll('#graph .node')){
      const old=previous.get(node.dataset.node);if(!old)continue;
      const c=node.querySelector('circle'),dx=old[0]-Number(c.getAttribute('cx')),dy=old[1]-Number(c.getAttribute('cy'));
      node.style.animation='none';
      animate(node,[{transform:`translate(${dx}px,${dy}px)`,opacity:.5},{transform:'translate(0,0)',opacity:1}],{duration:MOTION.reveal});
    }
    panel(document.querySelector('.case-panel'),100);
    profile();
  }
  const observer=typeof IntersectionObserver==='function'?new IntersectionObserver(entries=>{sceneInViewport=entries[0].isIntersecting;sync();},{threshold:.08}):null;
  observer?.observe(document.querySelector('.graph-container'));
  document.addEventListener('visibilitychange',sync);
  media.addEventListener('change',event=>{enabled=!event.matches;sync();});
  document.getElementById('motion-toggle').addEventListener('click',()=>{enabled=!enabled;sync();});
  sync();
  return {
    get reduced(){return !enabled;}, capture, reveal, panel, animate,
    cancel(element){running.get(element)?.cancel();running.delete(element);},
    setView(next){const changed=view!==next;view=next;sync();if(changed)panel(document.getElementById(`view-${next}`));},
  };
}
