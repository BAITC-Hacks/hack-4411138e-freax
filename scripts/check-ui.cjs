const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const browser = await chromium.launch({channel:'chrome',headless:true});
  const page = await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const output=path.resolve('output/playwright');fs.mkdirSync(output,{recursive:true});
  try {
    await page.goto(process.env.APP_URL || 'http://127.0.0.1:8765/');
    await page.locator('#theme-select').selectOption('light');
    assert.equal(await page.locator('#run').isEnabled(),false);
    await page.locator('#load-example').click();
    await page.locator('#batch-list .packet-name strong').first().waitFor();
    assert.equal(await page.locator('#batch-list .packet-file').count(),8);
    const filename=await page.locator('#batch-list .packet-name strong').first().innerText();
    for(const lang of ['kk','en','ru']){
      await page.locator(`[data-lang="${lang}"]`).click();
      assert.equal(await page.locator('html').getAttribute('lang'),lang);
      assert.equal(await page.locator('#batch-list .packet-name strong').first().innerText(),filename);
    }
    await page.locator('#run').click();
    await page.locator('#results').waitFor({state:'visible',timeout:90000});
    assert.match(await page.locator('#findings').innerText(),/цифрового развития/);
    assert.match(await page.locator('#run-method').innerText(),/без ИИ/);
    await page.locator('#finding-search').fill('цифрового развития');
    await page.locator('[data-lang="kk"]').click();
    assert.equal(await page.locator('#finding-search').inputValue(),'цифрового развития');
    assert.equal(await page.locator('#findings [data-finding]').count(),1);
    await page.locator('[data-lang="ru"]').click();
    await page.locator('#finding-search').fill('');
    await page.screenshot({path:path.join(output,'desktop-light.png')});
    await page.locator('#findings [data-finding="f2"]').click();
    await page.locator('#evidence[open]').waitFor();
    assert.equal(await page.locator('#left-document option').count(),8);
    assert(await page.locator('#left-text .linked').count());
    assert(await page.locator('#right-text .linked').count());
    await page.locator('#left-document').selectOption('d2');
    assert.equal(await page.locator('#right-document').inputValue(),'d2');
    await page.locator('#left-document').selectOption('d1');
    await page.locator('#pane-resizer').press('ArrowLeft');
    assert.equal(await page.locator('#pane-resizer').getAttribute('aria-valuenow'),'45');
    await page.locator('#pane-resizer').press('Home');
    await page.locator('#analyst-note').fill('Проверено по пункту 3.4.');
    await page.locator('#review-select').selectOption('confirmed');
    await page.locator('#evidence-close').click();
    assert.equal(await page.evaluate(()=>document.activeElement.getAttribute('data-finding')),'f2');
    await page.locator('#unreviewed-only').check();
    assert.equal(await page.locator('#findings [data-finding="f2"]').count(),0);
    await page.locator('#unreviewed-only').uncheck();
    await page.locator('#findings [data-finding="f2"]').click();
    assert.equal(await page.locator('#analyst-note').inputValue(),'Проверено по пункту 3.4.');
    await page.locator('#evidence-close').click();
    await page.locator('#tab-report').click();
    assert.match(await page.locator('#conclusion').innerText(),/Подтверждено аналитиком: 1/);
    const downloadEvent=page.waitForEvent('download');
    await page.locator('#download').click();
    const download=await downloadEvent;await download.saveAs(path.join(output,'conclusion.md'));
    const markdown=fs.readFileSync(path.join(output,'conclusion.md'),'utf8');
    assert.match(markdown,/SHA-256/);assert.match(markdown,/Комментарий аналитика: Проверено по пункту 3.4./);
    await page.locator('#tab-departments').click();
    await page.locator('#theme-select').selectOption('dark');
    await page.screenshot({path:path.join(output,'desktop-dark.png')});
    for(const width of [360,390,768,1024,1440]){
      await page.setViewportSize({width,height:900});
      for(const theme of ['light','dark']){
        await page.locator('#theme-select').selectOption(theme);
        assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Overflow at ${width}/${theme}`);
      }
    }
    await page.setViewportSize({width:390,height:844});
    await page.locator('#theme-select').selectOption('light');
    await page.screenshot({path:path.join(output,'mobile-light.png')});
    await page.locator('#theme-select').selectOption('dark');
    await page.locator('#findings [data-finding="f1"]').click();
    assert.match(await page.locator('#left-notice').innerText(),/Связанных абзацев/);
    await page.screenshot({path:path.join(output,'mobile-dark.png')});
    await page.locator('#evidence-close').click();
    await page.locator('[data-lang="en"]').click();
    await page.reload();
    assert.equal(await page.locator('html').getAttribute('lang'),'en');
    assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
    await page.goto(new URL('index.html',process.env.APP_URL || 'http://127.0.0.1:8765/').href);
    await page.locator('input[value="0"]').check();
    await page.getByRole('button',{name:'Проверить ответ',exact:true}).click();
    assert.match(await page.locator('.feedback').innerText(),/Пока неверно/);
    await page.locator('input[value="1"]').check();
    await page.getByRole('button',{name:'Проверить ещё раз'}).click();
    assert.match(await page.locator('#stats').innerText(),/Всего попыток\s*2/);
    await page.getByRole('button',{name:'Следующий кейс'}).click();
    await page.locator('input[value="2"]').check();
    await page.getByRole('button',{name:'Проверить ответ',exact:true}).click();
    await page.getByRole('button',{name:'Следующий кейс'}).click();
    await page.locator('input[value="0"]').check();
    await page.getByRole('button',{name:'Проверить ответ',exact:true}).click();
    assert.match(await page.locator('#stats').innerText(),/Кейсов решено\s*3 \/ 3/);
    assert.match(await page.locator('#stats').innerText(),/С первой попытки\s*2 \/ 3/);
    assert.match(await page.locator('#stats').innerText(),/Решено после объяснения\s*1 \/ 3/);
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:path.join(output,'training-mobile.png'),fullPage:true});
    assert.deepEqual(errors,[]);
    console.log('PASS: actual DOCX analysis, three locales, themes, source review, notes, export, responsive widths, preferences and practice; no JS errors.');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
