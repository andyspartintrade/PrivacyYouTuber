
// Mock browser env
global.localStorage = { getItem: ()=>null, setItem: ()=>{}, };
global.navigator = { language: 'en-US' };
global.document = {
  documentElement: { setAttribute: ()=>{} },
  querySelectorAll: ()=>[],
};
global.window = global;
global.CustomEvent = function(n,o){ this.type=n; this.detail=o&&o.detail; };
global.fetch = (url) => Promise.resolve({
  ok: true,
  json: () => Promise.resolve(require('C:/Users/andys/privacy-yt/web/i18n.json'))
});
