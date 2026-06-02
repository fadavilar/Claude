const cron = require('node-cron');
const WhatsAppManager = require('./whatsapp');
const Summarizer = require('./summarizer');
const config = require('./config');

const whatsapp = new WhatsAppManager();
const summarizer = new Summarizer();

async function runSummary() {
  console.log(`\n🔄 Generando resumen — ${new Date().toLocaleString('es-MX')}`);
  try {
    const messages = await whatsapp.getRecentMessages();

    if (messages.length === 0) {
      const text = '✅ Sin mensajes pendientes por el momento';
      await whatsapp.sendToResumenChat(text);
      console.log('✅ Resumen enviado: sin mensajes');
      return;
    }

    console.log(
      `📨 ${messages.length} conversaciones con mensajes en las últimas ${config.lookbackHours}h`
    );

    const summary = await summarizer.summarize(messages);
    const header = `📋 *Resumen WhatsApp* — ${new Date().toLocaleString('es-MX')}\n\n`;
    await whatsapp.sendToResumenChat(header + summary);
    console.log('✅ Resumen enviado al chat "Resumen"');
  } catch (err) {
    console.error('❌ Error al generar resumen:', err.message);
  }
}

async function main() {
  console.log('🚀 Iniciando agente resumen de WhatsApp...');

  if (!config.anthropicApiKey) {
    console.error(
      '❌ Falta ANTHROPIC_API_KEY en el archivo .env\n' +
      '   Copia .env.example a .env y agrega tu clave de API'
    );
    process.exit(1);
  }

  await whatsapp.initialize();

  // Ejecutar resumen inmediatamente al arrancar
  await runSummary();

  // Programar resúmenes periódicos
  cron.schedule(config.summaryInterval, runSummary, {
    timezone: 'America/Mexico_City',
  });
  console.log(`⏰ Resúmenes programados: ${config.summaryInterval}`);

  // Permitir trigger manual con !resumen desde el propio número
  whatsapp.getClient().on('message', async (msg) => {
    if (msg.fromMe && msg.body.trim().toLowerCase() === '!resumen') {
      console.log('📲 Trigger manual recibido');
      await runSummary();
    }
  });

  console.log('✅ Agente activo. Envía "!resumen" desde tu número para un resumen inmediato.');
}

main().catch((err) => {
  console.error('❌ Error fatal:', err);
  process.exit(1);
});
