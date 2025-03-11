import { Component, ElementRef, ViewChild, OnInit, AfterViewInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./styles.css']
})
export class AppComponent implements OnInit, AfterViewInit {
  apiUrl = 'https://pg2i4ekj00.execute-api.us-east-1.amazonaws.com/dev/classify';
  @ViewChild('videoElement') videoElement!: ElementRef;

  isProcessing = false;
  countdown = 15;
  progressPercentage = 0;
  interval: any;

  isHuman: boolean | null = null;
  confidence = 0;
  sagemakerResult = '';
  rekognitionResult = '';
  agreement = false;

  captured = false;
  capturedImage: string | null = null;
  aiBoxes: { left: number, top: number, size: number }[] = [];
  
  isCameraActive = false;
  videoStream: MediaStream | null = null;

  constructor(private http: HttpClient) {}

  ngOnInit() {
    // Initialize any data or settings when component loads
  }

  ngAfterViewInit() {
    // Start camera after the view is fully initialized
    setTimeout(() => {
      this.openCamera();
    }, 500);
  }

  triggerFileUpload() {
    const fileInput = document.getElementById('uploadInput') as HTMLInputElement;
    fileInput?.click();
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    
    if (input.files && input.files.length > 0) {
      const file = input.files[0];
      const reader = new FileReader();
      
      reader.onload = (e) => {
        this.capturedImage = e.target?.result as string;
        this.captured = true;
        this.generateAiBoxes();
        this.startProcessing();
      };
      
      reader.readAsDataURL(file);
    }
  }

  captureImage() {
    if (!this.isCameraActive) {
      this.openCamera();
    } else {
      this.takePhoto();
      this.startProcessing();
    }
  }
  
  openCamera() {
    navigator.mediaDevices.getUserMedia({ video: true })
      .then((stream) => {
        this.videoStream = stream;
        this.isCameraActive = true;
        setTimeout(() => {
          const videoEl = this.videoElement?.nativeElement;
          if (videoEl) {
            videoEl.srcObject = stream;
            videoEl.play().catch((err: Error) => console.error("Error playing video:", err));
          }
        }, 100);
      })
      .catch((error) => console.error("Camera access denied:", error));
  }
  
  takePhoto() {
    if (this.videoElement && this.videoElement.nativeElement) {
      const video = this.videoElement.nativeElement;
      const canvas = document.createElement('canvas');
      const context = canvas.getContext('2d');
      
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      
      if (context) {
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        this.capturedImage = canvas.toDataURL('image/png');
        this.captured = true;
        
        // Stop the camera
        this.stopCamera();
        
        // Generate AI boxes
        this.generateAiBoxes();
      }
    }
  }
  
  stopCamera() {
    this.isCameraActive = false;
    
    if (this.videoStream) {
      this.videoStream.getTracks().forEach(track => track.stop());
      this.videoStream = null;
    }
  }

  generateAiBoxes() {
    if (!this.captured || !this.capturedImage) {
      this.aiBoxes = [];
      return;
    }
  
    this.aiBoxes = [];
    for (let i = 0; i < 3; i++) {
      this.aiBoxes.push({
        left: Math.random() * 70 + 15,
        top: Math.random() * 70 + 15,
        size: Math.random() * 30 + 20
      });
    }
  }
  
  startProcessing() {
    this.isProcessing = true;
    this.countdown = 15;
    this.progressPercentage = 0;
    
    // Generate initial AI boxes
    this.generateAiBoxes();
    
    // Simulate API call with progress and moving AI boxes
    this.interval = setInterval(() => {
      this.countdown--;
      this.progressPercentage = ((15 - this.countdown) / 15) * 100;
      
      // Update AI box positions every second to simulate movement
      this.updateAiBoxPositions();
      
      if (this.countdown <= 0) {
        clearInterval(this.interval);
        this.simulateResults();
      }
    }, 1000);
    
    // Actual API call would be here
    // this.http.post(this.apiUrl, { image: this.capturedImage }).subscribe(...)
  }
  
  updateAiBoxPositions() {
    // Update existing AI boxes with new random positions
    this.aiBoxes = this.aiBoxes.map(box => {
      return {
        left: Math.random() * 70 + 15,  // Random position between 15% and 85%
        top: Math.random() * 70 + 15,   // Random position between 15% and 85%
        size: Math.random() * 20 + 25   // Random size between 25px and 45px
      };
    });
    
    // Occasionally add or remove a box to make it more dynamic
    if (Math.random() > 0.7) {
      if (this.aiBoxes.length < 5 && Math.random() > 0.5) {
        // Add a new box
        this.aiBoxes.push({
          left: Math.random() * 70 + 15,
          top: Math.random() * 70 + 15,
          size: Math.random() * 20 + 25
        });
      } else if (this.aiBoxes.length > 1) {
        // Remove a random box
        const indexToRemove = Math.floor(Math.random() * this.aiBoxes.length);
        this.aiBoxes.splice(indexToRemove, 1);
      }
    }
  }
  
  simulateResults() {
    this.isProcessing = false;
    
    // For demo purposes, generate random results
    this.isHuman = Math.random() > 0.3; // 70% chance of being human
    this.confidence = this.isHuman ? 0.7 + (Math.random() * 0.3) : Math.random() * 0.7;
    this.agreement = Math.random() > 0.2; // 80% chance of agreement
  }
  
  resetCapture() {
    this.captured = false;
    this.capturedImage = null;
    this.aiBoxes = [];
    this.isHuman = null;
    this.confidence = 0;
    this.agreement = false;
    this.isProcessing = false;
    
    if (this.interval) {
      clearInterval(this.interval);
    }
    
    // Restart the camera after reset
    this.openCamera();
  }
}