const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const config = require('./config');

class WhatsAppManager {
  constructor() {
    this.client = new Client({
      authStrategy: new LocalAuth(),
      puppeteer: {
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
      },
    });
    this.resumenChat = null;
    this.isReady = false;
    this._readyResolve = null;
  }

  initialize() {
    return new Promise((resolve, reject) => {
      this._readyResolve = resolve;

      this.client.on('qr', (qr) => {
        console.log('\n📱 Escanea este código QR con WhatsApp:\n');
        qrcode.generate(qr, { small: true });
      });

      this.client.on('authenticated', () => {
        console.log('✅ Autenticación exitosa');
      });

      this.client.on('ready', async () => {
        console.log('✅ WhatsApp conectado correctamente');
        this.isReady = true;
        await this._findResumenChat();
        resolve();
      });

      this.client.on('disconnected', (reason) => {
        console.log('❌ WhatsApp desconectado:', reason);
        this.isReady = false;
      });

      this.client.on('auth_failure', (msg) => {
        console.error('❌ Error de autenticación:', msg);
        reject(new Error(msg));
      });

      this.client.initialize();
    });
  }

  async _findResumenChat() {
    const chats = await this.client.getChats();
    this.resumenChat = chats.find(
      (c) => c.name === config.resumenChatName
    ) || null;

    if (this.resumenChat) {
      console.log(`✅ Chat "${config.resumenChatName}" encontrado`);
    } else {
      console.log(
        `⚠️  No se encontró el chat "${config.resumenChatName}".\n` +
        `   Por favor crea un grupo de WhatsApp llamado exactamente "${config.resumenChatName}"\n` +
        `   y agrégate a ti mismo. El agente enviará los resúmenes ahí.`
      );
    }
  }

  async getRecentMessages(hoursBack = config.lookbackHours) {
    if (!this.isReady) throw new Error('WhatsApp no está listo');

    const cutoff = Date.now() - hoursBack * 60 * 60 * 1000;
    const chats = await this.client.getChats();
    const result = [];

    for (const chat of chats) {
      if (chat.name === config.resumenChatName) continue;

      const messages = await chat.fetchMessages({ limit: 50 });
      const recent = messages.filter(
        (m) => !m.fromMe && m.timestamp * 1000 >= cutoff && m.body
      );

      if (recent.length === 0) continue;

      const contact = await chat.getContact().catch(() => null);
      const chatLabel = chat.isGroup
        ? `Grupo: ${chat.name}`
        : `Contacto: ${contact?.pushname || contact?.name || chat.name}`;

      result.push({
        chat: chatLabel,
        isGroup: chat.isGroup,
        unreadCount: chat.unreadCount,
        messages: recent.map((m) => ({
          body: m.body,
          timestamp: new Date(m.timestamp * 1000).toLocaleString('es-MX'),
          author: m._data.notifyName || m.author || 'Desconocido',
        })),
      });
    }

    return result;
  }

  async sendToResumenChat(text) {
    if (!this.isReady) throw new Error('WhatsApp no está listo');

    if (!this.resumenChat) {
      await this._findResumenChat();
    }

    if (!this.resumenChat) {
      console.error(
        `❌ No se puede enviar: el chat "${config.resumenChatName}" no existe todavía.`
      );
      return false;
    }

    await this.resumenChat.sendMessage(text);
    return true;
  }

  getClient() {
    return this.client;
  }
}

module.exports = WhatsAppManager;
