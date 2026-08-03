const { chromium } = require("playwright-core");
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");

const seed = JSON.parse(fs.readFileSync(process.env.E2E_SEED_PATH || path.resolve(__dirname,"../../.tmp/e2e-seed.json"),"utf8").replace(/^\uFEFF/,""));
const baseURL=process.env.E2E_BASE_URL||"http://127.0.0.1:58002";
const apiURL=process.env.E2E_API_URL||"http://127.0.0.1:58001/api/v1";
const chrome=process.env.CHROME_PATH||"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const open=seed.instances.find(x=>x.status==="OPEN"), scheduled=seed.instances.find(x=>x.status==="SCHEDULED");
assert(open&&scheduled,"El sembrado debe contener OPEN y SCHEDULED");

async function login(page,account){
  await page.goto(`${baseURL}/login`); await page.getByLabel("Email").fill(account.email); await page.getByLabel(/Contrase/).fill(seed.password);
  await page.getByRole("button",{name:"Ingresar"}).click(); await page.waitForFunction(role=>JSON.parse(localStorage.getItem("ecoevent360.user")||"{}").role===role,account.role);
  return page.evaluate(()=>localStorage.getItem("ecoevent360.access_token"));
}
async function api(page,token,method,url,body){return page.evaluate(async({apiURL,token,method,url,body})=>{const response=await fetch(apiURL+url,{method,headers:{Authorization:`Bearer ${token}`,...(body&&!(body instanceof FormData)?{"Content-Type":"application/json"}:{})},body:body?JSON.stringify(body):undefined});return {status:response.status,text:await response.text()};},{apiURL,token,method,url,body});}

async function workerFlow(browser,viewport,label,mutate){
  const context=await browser.newContext({viewport});const page=await context.newPage();const errors=[];page.on("pageerror",e=>errors.push(e.message));
  const token=await login(page,seed.users.worker);await page.goto(`${baseURL}/worker/mis-bitacoras`);await page.getByText(/asignada/).first().waitFor();
  await page.goto(`${baseURL}/worker/mis-bitacoras/${scheduled.id}`);await page.getByText(/programada/i).waitFor();
  assert.equal(await page.getByText("Confirmado").locator("..").getByRole("checkbox").isDisabled(),true);assert.equal(await page.locator('input[type="file"]').isDisabled(),true);assert.equal(await page.getByRole("button",{name:/Enviar a revisiÃ³n/}).count(),0);
  const detail=JSON.parse((await api(page,token,"GET",`/logbook-instances/${scheduled.id}`)).text);const item=detail.version.sections[0].items[0];
  assert.equal((await api(page,token,"PUT",`/logbook-assignments/${scheduled.assignment_id}/responses`,{item_id:item.id,result_status:"COMPLETED",boolean_value:true,is_not_applicable:false})).status,409);
  if(mutate){
    await page.goto(`${baseURL}/worker/mis-bitacoras/${open.id}`);await page.getByText("Confirmado").waitFor();await page.getByText("Confirmado").locator("..").getByRole("checkbox").click();await page.getByText("Cambios guardados",{exact:true}).waitFor();
    const persisted=JSON.parse((await api(page,token,"GET",`/logbook-instances/${open.id}`)).text);assert.equal(persisted.assignments[0].responses.some(response=>response.boolean_value===true),true,"La confirmación no persistió");
    const photo=path.resolve(__dirname,"../../.tmp/e2e-photo.png");assert.equal(fs.existsSync(photo),true,"Falta la fotografía PNG temporal válida");
    await page.locator('input[type="file"]').setInputFiles(photo);await page.getByRole("button",{name:"Ver e2e-photo.png"}).waitFor();await page.getByRole("button",{name:"Ver e2e-photo.png"}).click();await page.getByRole("img",{name:/Evidencia/}).waitFor();await page.getByLabel(/Cerrar foto/).click();
    await page.getByRole("button",{name:"Eliminar"}).click();await page.getByRole("button",{name:"Eliminar fotografía"}).click();await page.getByRole("button",{name:"Ver e2e-photo.png"}).waitFor({state:"detached"});
    await page.locator('input[type="file"]').setInputFiles(photo);await page.getByRole("button",{name:"Ver e2e-photo.png"}).waitFor();
    await page.getByRole("button",{name:/Enviar a revisi/}).click();await page.getByRole("button",{name:/Enviar bit/}).click();await page.reload();await page.getByText(/Enviada|SUBMITTED/i).first().waitFor();
    await page.goto(`${baseURL}/worker/mis-bitacoras/${scheduled.id}`);assert.equal(await page.getByRole("button",{name:"Ver e2e-photo.png"}).count(),0);await page.goto(`${baseURL}/worker/mis-bitacoras/${open.id}`);await page.getByRole("button",{name:"Ver e2e-photo.png"}).waitFor();
  }
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth),false,`${label}: overflow`);assert.deepEqual(errors,[]);await page.screenshot({path:path.resolve(__dirname,`../../.tmp/worker-${label}.png`),fullPage:true});await context.close();
}

async function denied(browser,key,url,expected){const context=await browser.newContext({viewport:{width:1440,height:900}}),page=await context.newPage();const token=await login(page,seed.users[key]);const result=await api(page,token,"GET",url);assert(expected.includes(result.status),`${key}: API devolvió ${result.status}`);const direct=key==="other_supervisor"?`/supervisor/bitacoras/${open.id}`:key==="foreign_client"?`/client/eventos/${seed.event_id}`:`/worker/mis-bitacoras/${open.id}`;await page.goto(baseURL+direct);await page.waitForTimeout(1200);assert.equal((await page.locator("body").innerText()).includes("Fotografía del resultado"),false,`${key}: mostró datos restringidos`);await context.close();}

(async()=>{const browser=await chromium.launch({headless:true,executablePath:chrome});await workerFlow(browser,{width:1440,height:900},"desktop",true);await workerFlow(browser,{width:390,height:844},"mobile",false);await denied(browser,"outsider",`/logbook-instances/${open.id}`,[403,404]);await denied(browser,"other_supervisor",`/logbook-instances/${open.id}`,[403,404]);await denied(browser,"foreign_client",`/client/logbooks/${open.id}`,[403,404]);const context=await browser.newContext(),page=await context.newPage(),token=await login(page,seed.users.own_client);assert.equal((await api(page,token,"GET",`/client/logbooks/${open.id}`)).status,200);await page.goto(`${baseURL}/client/eventos/${seed.event_id}`);await page.waitForTimeout(1200);const clientBody=await page.locator("body").innerText();assert.equal(clientBody.includes("Editar participantes futuros"),false);assert.equal(clientBody.includes("Fotografía del resultado"),false);await context.close();await browser.close();console.log("Real worker/security E2E passed");})().catch(e=>{console.error(e);process.exit(1)});
