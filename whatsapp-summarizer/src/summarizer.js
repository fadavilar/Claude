const Anthropic = require('@anthropic-ai/sdk');
const config = require('./config');

const SYSTEM_PROMPT = `Eres un asistente que analiza mensajes de WhatsApp y genera resúmenes priorizados en español.

Tu tarea es clasificar y resumir los mensajes recibidos según la urgencia de respuesta en estas categorías:

🔴 URGENTE (responder en menos de 1 hora)
- Mensajes que requieren acción inmediata
- Solicitudes con plazos inminentes
- Emergencias o situaciones críticas
- Preguntas directas que esperan respuesta rápida

🟡 ALTA PRIORIDAD (responder hoy)
- Mensajes importantes del día
- Solicitudes con plazo para hoy
- Temas de trabajo o negocios activos
- Confirmaciones o decisiones pendientes

🟢 MEDIA PRIORIDAD (responder esta semana)
- Conversaciones en curso sin urgencia
- Coordinaciones futuras
- Seguimientos no críticos

⚪ BAJA / INFORMATIVO (sin urgencia)
- Noticias, artículos, memes compartidos
- Conversaciones sociales casuales
- Notificaciones automáticas
- Mensajes que no requieren respuesta

Formato de respuesta:
- Usa las categorías con sus emojis exactamente como se muestran
- Para cada mensaje relevante indica: chat de origen, resumen breve del contenido y por qué tiene esa prioridad
- Si una categoría no tiene mensajes, omítela completamente
- Sé conciso pero informativo
- Al final incluye un conteo total: "Total: X mensajes de Y conversaciones"
- Si no hay mensajes que resumir, indica "✅ Sin mensajes pendientes por el momento"`;

class Summarizer {
  constructor() {
    this.client = new Anthropic({ apiKey: config.anthropicApiKey });
  }

  async summarize(chatMessages) {
    if (!chatMessages || chatMessages.length === 0) {
      return '✅ Sin mensajes pendientes por el momento';
    }

    const userContent = this._buildUserContent(chatMessages);

    const response = await this.client.messages.create({
      model: 'claude-opus-4-8',
      max_tokens: 2048,
      thinking: { type: 'adaptive' },
      system: [
        {
          type: 'text',
          text: SYSTEM_PROMPT,
          cache_control: { type: 'ephemeral' },
        },
      ],
      messages: [
        {
          role: 'user',
          content: userContent,
        },
      ],
    });

    const textBlock = response.content.find((b) => b.type === 'text');
    return textBlock ? textBlock.text : '⚠️ No se pudo generar el resumen';
  }

  _buildUserContent(chatMessages) {
    const lines = ['Aquí están los mensajes recientes a resumir:\n'];

    for (const chat of chatMessages) {
      lines.push(`--- ${chat.chat} (no leídos: ${chat.unreadCount}) ---`);
      for (const msg of chat.messages) {
        const author = chat.isGroup ? `[${msg.author}] ` : '';
        lines.push(`  ${msg.timestamp} | ${author}${msg.body}`);
      }
      lines.push('');
    }

    lines.push(
      `\nTotal de conversaciones con mensajes: ${chatMessages.length}`
    );

    return lines.join('\n');
  }
}

module.exports = Summarizer;
