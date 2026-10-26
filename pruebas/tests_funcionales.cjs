/* Dos casos de sistema en Chromium, con aplicación y SQLite reales locales. */
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
let playwright;
try { playwright = require('playwright'); }
catch (_) {
  const roots = [process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES].filter(Boolean);
  playwright = require(require.resolve('playwright', {paths: roots}));
}
const playwrightVersion = require(require.resolve('playwright/package.json', {paths:[__dirname,process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES].filter(Boolean)})).version;
const [baseURL, database, output, variant, python] = process.argv.slice(2);
const valid = {name: 'Ana Prueba', email: 'ana.prueba@example.com',
  subject: 'Consulta académica', message: 'Solicito información del programa.'};
function db(reset=false) {
  const code = reset
    ? "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.execute('DELETE FROM contacts'); c.execute(\"DELETE FROM sqlite_sequence WHERE name='contacts'\"); c.commit(); c.close(); print('[]')"
    : "import sqlite3,sys,json; c=sqlite3.connect(sys.argv[1]); c.row_factory=sqlite3.Row; print(json.dumps([dict(r) for r in c.execute('SELECT * FROM contacts ORDER BY id')],ensure_ascii=False)); c.close()";
  return JSON.parse(execFileSync(python, ['-c', code, database], {encoding:'utf8'}));
}
function check(record, label, passed) {
  record.actual_assertions.push({label, passed: Boolean(passed)});
}
async function dom(page) {
  return await page.evaluate(() => ({
    title: document.title,
    environment: document.getElementById('environment')?.textContent,
    status: document.getElementById('status')?.textContent,
    status_class: document.getElementById('status')?.className,
    email_error: document.getElementById('email-error')?.textContent,
    name_error: document.getElementById('name-error')?.textContent,
    button_disabled: document.querySelector('button')?.disabled,
    field_values: Object.fromEntries(['name','email','subject','message'].map(k => [k,document.getElementById(k)?.value])),
    stylesheet_links: Array.from(document.querySelectorAll('link[rel="stylesheet"]')).map(n=>n.href),
    script_links: Array.from(document.querySelectorAll('script[src]')).map(n=>n.src)
  }));
}
async function runCase(browser, id) {
  const started = new Date();
  const record = {id, variant,
    name: id === 'F01' ? 'Formulario desde la raíz y envío válido' : 'Correo inválido con retroalimentación visible',
    started_at_utc: started.toISOString(),
    execution: 'real local Chromium execution, no HTTP mocks',
    inputs: id === 'F01' ? valid : {...valid,email:'correo-invalido'},
    expected: id === 'F01'
      ? {page:'/',assets_status:200,environment:'testing',post_status:201,success:'Tu mensaje fue enviado correctamente.',new_rows:1,fields_cleared:true,button_enabled:true}
      : {page:'/static/index.html',post_status:422,email_error:'Ingresa un correo electrónico válido.',new_rows:0,button_enabled:true},
    actual_assertions:[],observed:{http:[],console_errors:[],rows_before:db(true)},
    environment:{APP_ENV:'testing',base_url:baseURL,additional_allowed_origin:baseURL,
      browser:'Chromium',browser_version:browser.version(),node_version:process.version,playwright_version:playwrightVersion,
      database_scope:'temporary copy of the application'}
  };
  const context = await browser.newContext({viewport:{width:1440,height:1050},locale:'es-ES'});
  const page = await context.newPage();
  page.on('response', response => {
    if(response.url().startsWith(baseURL)) {
      record.observed.http.push({method:response.request().method(),path:new URL(response.url()).pathname,status:response.status(),resource_type:response.request().resourceType()});
    }
  });
  page.on('console', msg => {if(msg.type()==='error')record.observed.console_errors.push(msg.text());});
  page.on('pageerror', err => record.observed.console_errors.push(err.message));
  try {
    const target = id === 'F01' ? '/' : '/static/index.html';
    const navigation = await page.goto(baseURL+target,{waitUntil:'networkidle',timeout:10000});
    check(record,'La página HTML responde HTTP 200',navigation.status()===200);
    record.observed.dom_after_load = await dom(page);
    const css = record.observed.http.find(r=>r.path.endsWith('/styles.css'));
    const js = record.observed.http.find(r=>r.path.endsWith('/app.js'));
    check(record,'La hoja de estilos responde HTTP 200',css?.status===200);
    check(record,'El JavaScript responde HTTP 200',js?.status===200);
    if(css?.status!==200 || js?.status!==200) {
      record.observed.not_reached = ['Carga del ambiente por JavaScript','Envío del formulario','Aserciones posteriores al envío'];
    } else {
      await page.waitForFunction(()=>document.getElementById('environment')?.textContent==='testing',null,{timeout:5000});
      check(record,'La interfaz muestra el ambiente testing',(await page.locator('#environment').textContent())==='testing');
      for(const [field,value] of Object.entries(record.inputs)) await page.locator('#'+field).fill(value);
      const responsePromise = page.waitForResponse(r=>r.url()===baseURL+'/api/contact' && r.request().method()==='POST',{timeout:5000});
      await page.locator('button[type="submit"]').click();
      const response = await responsePromise;
      const body = await response.json();
      record.observed.post_response={status:response.status(),body};
      await page.waitForFunction(()=>document.querySelector('button')?.disabled===false,null,{timeout:5000});
      record.observed.dom_after_submit = await dom(page);
      record.observed.rows_after = db();
      if(id==='F01') {
        check(record,'El envío responde HTTP 201',response.status()===201);
        check(record,'El mensaje de éxito aparece en la interfaz',record.observed.dom_after_submit.status==='Tu mensaje fue enviado correctamente.');
        check(record,'SQLite guarda exactamente una fila',record.observed.rows_after.length===1);
        check(record,'Los campos guardados coinciden con los enviados',record.observed.rows_after.length===1 && Object.entries(valid).every(([k,v])=>record.observed.rows_after[0][k]===v));
        check(record,'El formulario queda vacío',Object.values(record.observed.dom_after_submit.field_values).every(v=>v===''));
      } else {
        check(record,'El envío responde HTTP 422',response.status()===422);
        check(record,'El error aparece junto al correo',record.observed.dom_after_submit.email_error==='Ingresa un correo electrónico válido.');
        check(record,'El estado visual indica fallo',record.observed.dom_after_submit.status_class==='status failure');
        check(record,'La respuesta identifica el campo email','email' in (body.errors||{}));
        check(record,'SQLite no recibe filas inválidas',record.observed.rows_after.length===0);
      }
      check(record,'El botón vuelve a quedar habilitado',record.observed.dom_after_submit.button_disabled===false);
    }
  } catch(error) {
    record.observed.execution_error={name:error.name,message:error.message,stack:error.stack};
    check(record,'La ejecución del caso finaliza sin excepciones',false);
  } finally {
    record.observed.rows_after ??= db();
    record.finished_at_utc = new Date().toISOString();
    record.duration_seconds=(Date.now()-started.getTime())/1000;
    record.status=record.actual_assertions.every(x=>x.passed)?'APROBADO':'FALLIDO';
    fs.mkdirSync(output,{recursive:true});
    fs.writeFileSync(path.join(output,id+'.json'),JSON.stringify(record,null,2)+'\n');
    console.log(JSON.stringify(record));
    await context.close();
  }
  return record.status==='APROBADO';
}
(async()=>{
  const launch={headless:true,args:['--no-sandbox','--disable-dev-shm-usage']};
  if(process.env.QA_CHROMIUM_EXECUTABLE) {
    launch.executablePath=process.env.QA_CHROMIUM_EXECUTABLE;
    if(process.platform!=='win32')fs.chmodSync(launch.executablePath,0o755);
  }
  const browser=await playwright.chromium.launch(launch);
  let all=true;
  try {for(const id of ['F01','F02']) all=(await runCase(browser,id))&&all;}
  finally {await browser.close();}
  process.exitCode=all?0:1;
})().catch(error=>{console.error(error.stack);process.exitCode=2;});
