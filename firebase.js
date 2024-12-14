const admin = require('firebase-admin');

// Firebase private key'inizi environment variable'dan alın
admin.initializeApp({
  credential: admin.credential.cert({
    projectId: process.env.FIREBASE_PROJECT_ID,
    privateKey: process.env.FIREBASE_PRIVATE_KEY.replace(/\\n/g, '\n'),
    clientEmail: process.env.FIREBASE_CLIENT_EMAIL,
  }),
});

console.log('Firebase Admin SDK başarıyla başlatıldı!');
