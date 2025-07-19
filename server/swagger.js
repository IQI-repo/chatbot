const swaggerJsdoc = require('swagger-jsdoc');
const swaggerUi = require('swagger-ui-express');

// Swagger definition
const swaggerOptions = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'Chatbot API Documentation',
      version: '1.0.0',
      description: 'API documentation for the chatbot server',
      contact: {
        name: 'API Support',
      },
    },
    servers: [
      {
        url: '/api',
        description: 'API Server',
      },
    ],
  },
  // Path to the API docs
  apis: [
    './routes/*.js',
    './controllers/*.js',
    './app.js',
  ],
};

const swaggerSpec = swaggerJsdoc(swaggerOptions);

module.exports = {
  swaggerUi,
  swaggerSpec,
};
