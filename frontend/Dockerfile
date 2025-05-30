FROM node:18-alpine

# Установка рабочей директории
WORKDIR /app

# Копирование package.json и package-lock.json
COPY package*.json ./

# Установка зависимостей
RUN npm ci --only=production

# Копирование исходного кода
COPY . .

# Сборка приложения
RUN npm run build

# Порт для Next.js
EXPOSE 3000

# Переменная для production
ENV NODE_ENV=production

# Команда запуска
CMD ["npm", "start"] 