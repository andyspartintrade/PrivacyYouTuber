s=open('scripts/_catpop_test3.html',encoding='utf-8').read()
s=s.replace('document.getElementById("RESULT").textContent=window.__RESULT;',
 'const cs=getComputedStyle(document.getElementById("cat-pop"));document.getElementById("RESULT").textContent="innerWidth="+window.innerWidth+" | popWidth="+document.getElementById("cat-pop").getBoundingClientRect().width+" | cssWidth="+cs.width+" | gridCols="+getComputedStyle(document.querySelector(".pop-page-grid")).gridTemplateColumns+" | items="+document.querySelectorAll(".pop-page-grid .tag-pop-item").length;')
open('scripts/_catpop_test4.html','w',encoding='utf-8').write(s)
