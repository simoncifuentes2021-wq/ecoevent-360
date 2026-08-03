const { chromium } = require("playwright-core");
const assert = require("node:assert/strict");

const baseURL = process.env.E2E_BASE_URL || "http://127.0.0.1:58002";
const chrome = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const eventId = "11111111-1111-4111-8111-111111111111";
const workerId = "22222222-2222-4222-8222-222222222222";
const worker2Id = "33333333-3333-4333-8333-333333333333";
const versionId = "44444444-4444-4444-8444-444444444444";
let series = [];
let occurrences = [];

const user = {id:"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",email:"admin.e2e@example.test",full_name:"Admin E2E",role:"ADMIN",is_active:true};
const event = {id:eventId,name:"Evento E2E recurrencia",status:"ACTIVE",start_date:"2026-08-01",end_date:"2026-12-31",country:"Chile",city:"Santiago",hidden_from_operations:false};
const staff = [
  {event_id:eventId,user_id:workerId,user:{id:workerId,full_name:"María E2E",email:"maria@example.test",role:"WORKER"}},
  {event_id:eventId,user_id:worker2Id,user:{id:worker2Id,full_name:"Simón E2E",email:"simon@example.test",role:"WORKER"}},
];
const template = {id:"55555555-5555-4555-8555-555555555555",name:"Limpieza E2E",status:"ACTIVE",versions:[{id:versionId,version_number:1,status:"PUBLISHED"}]};

async function mockApi(page) {
  await page.route("**/*", async route => {
    const req=route.request();
    if (!["fetch","xhr"].includes(req.resourceType())) return route.continue();
    const url=new URL(req.url()), path=url.pathname.replace(/^\/api\/v\d+/,"");
    const json=(body,status=200)=>route.fulfill({status,contentType:"application/json",body:JSON.stringify(body)});
    if(path==="/auth/me") return json(user);
    if(path===`/events/${eventId}`) return json(event);
    if(path.includes("dashboard")||path.includes("summary")||path.includes("metrics")) return json({items:[],total:0,completion_percentage:0,participation_percentage:0,approval_percentage:0});
    if(path===`/events/${eventId}/logbooks`) return json({items:[],total:0,page:1,limit:50});
    if(path===`/events/${eventId}/staff`) return json(staff);
    if(path==="/logbook-templates") return json({items:[template],total:1,page:1,limit:50});
    if(path===`/logbook-templates/${template.id}`) return json(template);
    if(path==="/logbook-recurrences/preview") return json({dates:["2026-08-02","2026-08-03","2026-08-09","2026-08-10"],truncated:false,monthly_rule:"SKIP_INVALID_DAY"});
    if(path===`/events/${eventId}/logbook-recurrences`&&req.method()==="GET") return json(series);
    if(path===`/events/${eventId}/logbook-recurrences`&&req.method()==="POST") {
      const body=req.postDataJSON(); const created={id:"66666666-6666-4666-8666-666666666666",event_id:eventId,template_id:template.id,template_version_id:versionId,name:"Limpieza E2E",assignment_mode:body.assignment_mode,client_visibility:false,frequency:body.frequency,interval:body.interval,weekdays:body.weekdays,start_date:body.start_date,end_mode:body.end_mode,max_occurrences:body.max_occurrences,opens_at_local:body.opens_at_local,due_at_local:body.due_at_local,timezone:body.timezone,status:"ACTIVE",next_occurrence_date:"2026-08-02",generated_count:4,revision:1,participant_ids:body.participant_ids,occurrence_counts:{SCHEDULED:4},created_at:new Date().toISOString()};
      series=[created]; occurrences=["2026-08-02","2026-08-03","2026-08-09","2026-08-10"].map((d,i)=>({id:`77777777-7777-4777-8777-77777777777${i}`,event_id:eventId,template_id:template.id,template_version_id:versionId,name:"Limpieza E2E",operational_stage:"GENERAL",assignment_mode:"INDIVIDUAL",status:"SCHEDULED",client_visibility:false,created_at:new Date().toISOString(),recurrence_series_id:created.id,occurrence_date:d,occurrence_modified:false})); return json(created,201);
    }
    if(series[0]&&path===`/logbook-recurrences/${series[0].id}/occurrences`) return json(occurrences);
    if(series[0]&&path===`/logbook-recurrences/${series[0].id}`&&req.method()==="PATCH") {const body=req.postDataJSON();series[0]={...series[0],participant_ids:body.participant_ids,revision:2};return json(series[0]);}
    if(series[0]&&path.endsWith("/pause")){series[0]={...series[0],status:"PAUSED"};return json(series[0]);}
    if(series[0]&&path.endsWith("/resume")){series[0]={...series[0],status:"ACTIVE"};return json(series[0]);}
    if(series[0]&&path.endsWith("/finish")){series[0]={...series[0],status:"FINISHED"};return json(series[0]);}
    if(series[0]&&path.endsWith("/skip")){occurrences=occurrences.filter(x=>x.occurrence_date!==req.postDataJSON().occurrence_date);return json(series[0]);}
    if(series[0]&&path.endsWith("/reschedule")){const body=req.postDataJSON(), item=occurrences.find(x=>x.occurrence_date===body.occurrence_date);item.original_occurrence_date=item.occurrence_date;item.occurrence_date=body.replacement_date;return json(item);}
    return json({items:[],total:0,page:1,limit:50});
  });
}

async function run(viewport,label){
  const browser=await chromium.launch({headless:true,executablePath:chrome});
  const context=await browser.newContext({viewport}); const page=await context.newPage(); const errors=[];
  page.on("pageerror",e=>errors.push(e.message));
  await mockApi(page);
  await page.addInitScript(({user})=>{localStorage.setItem("ecoevent360.access_token","e2e-token");localStorage.setItem("ecoevent360.user",JSON.stringify(user));},{user});
  await page.goto(`${baseURL}/admin/eventos/${eventId}`,{waitUntil:"networkidle"});
  await page.getByRole("button",{name:/Bit/i}).click();
  await page.getByRole("button",{name:"Crear recurrencia"}).click();
  await page.getByText("María E2E").click(); await page.getByText("Simón E2E").click();
  await page.getByLabel("Domingo").check(); await page.getByLabel("Lunes").check(); await page.getByLabel("Martes").uncheck();
  await page.getByLabel("Terminar por").selectOption("COUNT"); await page.getByLabel("Repeticiones").fill("4");
  await page.getByRole("button",{name:"Vista previa"}).click(); await page.getByText("02-08-2026").waitFor();
  await page.getByRole("button",{name:"Revisar y crear"}).click(); assert.equal(await page.getByRole("dialog").count(),1);
  const dialogBox=await page.getByRole("dialog").boundingBox(); assert(dialogBox&&dialogBox.x>=0&&dialogBox.width<=viewport.width,"diálogo fuera del viewport");
  await page.getByRole("button",{name:"Crear serie"}).dblclick(); await page.getByText("Limpieza E2E").waitFor(); assert.equal(series.length,1,"doble envío creó más de una serie");
  await page.getByRole("button",{name:"Ver historial y próximas fechas"}).click(); await page.getByText(/02-08-2026/).last().waitFor();
  await page.getByRole("button",{name:"Pausar"}).click(); await page.getByRole("button",{name:"Reanudar"}).click();
  await page.getByRole("button",{name:"Reprogramar"}).first().click(); await page.getByLabel("Nueva fecha").fill("2026-08-04"); await page.getByLabel("Motivo").fill("Ajuste E2E"); await page.getByRole("button",{name:"Reprogramar",exact:true}).last().click(); await page.getByText(/04-08-2026/).waitFor();
  await page.getByRole("button",{name:"Omitir"}).first().click(); await page.getByLabel("Motivo").fill("Omisión E2E"); await page.getByRole("button",{name:"Omitir fecha"}).click(); assert.equal(occurrences.length,3);
  await page.getByRole("button",{name:"Editar participantes futuros"}).click(); await page.getByLabel("Simón E2E").uncheck(); await page.getByRole("button",{name:"Aplicar hacia el futuro"}).click(); assert.deepEqual(series[0].participant_ids,[workerId]);
  await page.getByRole("button",{name:"Finalizar"}).click(); await page.getByText(/Finalizada/).waitFor();
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth); assert.equal(overflow,false,`${label}: overflow horizontal`);
  assert.deepEqual(errors,[],`${label}: errores de página`);
  await page.screenshot({path:`../.tmp/recurrence-${label}.png`,fullPage:true}); await browser.close();
}

(async()=>{await run({width:1440,height:900},"desktop");series=[];occurrences=[];await run({width:390,height:844},"mobile");console.log("E2E recurrence browser: desktop and mobile passed");})().catch(error=>{console.error(error);process.exit(1);});
