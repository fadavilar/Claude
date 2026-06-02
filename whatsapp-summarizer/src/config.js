require('dotenv').config();

module.exports = {
  anthropicApiKey: process.env.ANTHROPIC_API_KEY,
  summaryInterval: process.env.SUMMARY_INTERVAL || '0 * * * *',
  lookbackHours: parseInt(process.env.LOOKBACK_HOURS) || 24,
  resumenChatName: process.env.RESUMEN_CHAT_NAME || 'Resumen',
};
