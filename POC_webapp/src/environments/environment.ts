// src/environments/environment.ts (development)
export const environment = {
    production: false,
    apiUrl: 'http://localhost:4200/api' // Development API URL
  };
  
  // src/environments/environment.prod.ts (production)
  export const environment = {
    production: true,
    apiUrl: 'https://pg2i4ekj00.execute-api.us-east-1.amazonaws.com/dev/classify'
  };