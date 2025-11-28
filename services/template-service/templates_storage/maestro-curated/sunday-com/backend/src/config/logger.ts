import winston from 'winston';

// Define log levels
const levels = {
  error: 0,
  warn: 1,
  info: 2,
  http: 3,
  debug: 4,
};

// Define log level based on environment
const level = (): string => {
  const env = process.env.NODE_ENV || 'development';
  const isDevelopment = env === 'development';
  return isDevelopment ? 'debug' : 'warn';
};

// Define log colors
const colors = {
  error: 'red',
  warn: 'yellow',
  info: 'green',
  http: 'magenta',
  debug: 'white',
};

winston.addColors(colors);

// Define log format
const format = winston.format.combine(
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss:ms' }),
  winston.format.colorize({ all: true }),
  winston.format.printf(
    (info) => `${info.timestamp} ${info.level}: ${info.message}`,
  ),
);

// Define transports
const transports = [
  new winston.transports.Console(),
  new winston.transports.File({
    filename: 'logs/error.log',
    level: 'error',
  }),
  new winston.transports.File({ filename: 'logs/all.log' }),
];

// Create logger
export const logger = winston.createLogger({
  level: level(),
  levels,
  format,
  transports,
});

// Custom logging methods for different contexts
export class Logger {
  static request(message: string, meta?: any): void {
    logger.http(message, meta);
  }

  static database(message: string, meta?: any): void {
    logger.debug(`[DATABASE] ${message}`, meta);
  }

  static auth(message: string, meta?: any): void {
    logger.info(`[AUTH] ${message}`, meta);
  }

  static security(message: string, meta?: any): void {
    logger.warn(`[SECURITY] ${message}`, meta);
  }

  static business(message: string, meta?: any): void {
    logger.info(`[BUSINESS] ${message}`, meta);
  }

  static performance(message: string, duration: number, meta?: any): void {
    logger.info(`[PERFORMANCE] ${message} - ${duration}ms`, meta);
  }

  static websocket(message: string, meta?: any): void {
    logger.debug(`[WEBSOCKET] ${message}`, meta);
  }

  static cache(message: string, meta?: any): void {
    logger.debug(`[CACHE] ${message}`, meta);
  }

  static api(message: string, meta?: any): void {
    logger.debug(`[API] ${message}`, meta);
  }

  static error(message: string, error?: Error, meta?: any): void {
    const errorMeta = {
      ...meta,
      stack: error?.stack,
      name: error?.name,
    };
    logger.error(`${message}: ${error?.message || 'Unknown error'}`, errorMeta);
  }

  static audit(action: string, userId: string, resource: string, meta?: any): void {
    logger.info(`[AUDIT] ${action} by user ${userId} on ${resource}`, meta);
  }
}

export default logger;