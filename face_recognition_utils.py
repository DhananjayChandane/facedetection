import cv2
import numpy as np
import face_recognition
import os
import pickle
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FaceUtils:
    def __init__(self, encodings_dir='face_encodings'):
        self.encodings_dir = encodings_dir
        os.makedirs(encodings_dir, exist_ok=True)
        self.known_encodings = {}
        self.load_known_encodings()
    
    def load_known_encodings(self):
        """Load all saved face encodings"""
        try:
            if os.path.exists('known_faces.dat'):
                with open('known_faces.dat', 'rb') as f:
                    self.known_encodings = pickle.load(f)
                logger.info(f"Loaded {len(self.known_encodings)} known face encodings")
        except Exception as e:
            logger.error(f"Error loading encodings: {e}")
            self.known_encodings = {}
    
    def save_known_encodings(self):
        """Save all face encodings to file"""
        try:
            with open('known_faces.dat', 'wb') as f:
                pickle.dump(self.known_encodings, f)
        except Exception as e:
            logger.error(f"Error saving encodings: {e}")
    
    def extract_face_encoding(self, image):
        """
        Extract face encoding from image
        Returns: numpy array or None
        """
        try:
            # Convert BGR to RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Find all faces in the image
            face_locations = face_recognition.face_locations(rgb_image, model='hog')
            
            if not face_locations:
                logger.warning("No faces detected in image")
                return None
            
            # Get encodings for all faces
            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
            
            if not face_encodings:
                logger.warning("Could not extract face encoding")
                return None
            
            # Return the first face encoding (assuming one face per image)
            encoding = face_encodings[0]
            
            # Log face detection
            logger.info(f"Face detected. Encoding shape: {encoding.shape}")
            
            return encoding
            
        except Exception as e:
            logger.error(f"Error extracting face encoding: {e}")
            return None
    
    def compare_faces(self, encoding1, encoding2, threshold=0.6):
        """
        Compare two face encodings
        Returns: True if match, False otherwise
        """
        try:
            if encoding1 is None or encoding2 is None:
                return False
            
            # Calculate Euclidean distance
            distance = np.linalg.norm(encoding1 - encoding2)
            
            # Log comparison
            logger.info(f"Face distance: {distance:.4f}, Threshold: {threshold}")
            
            return distance < threshold
            
        except Exception as e:
            logger.error(f"Error comparing faces: {e}")
            return False
    
    def recognize_face_from_list(self, unknown_encoding, known_encodings, tolerance=0.6):
        """
        Compare an unknown face encoding with a list of known encodings.
        Returns (face_index, distance) if match found, else (None, None)
        """
        try:
            if len(known_encodings) == 0:
                return None, None
            
            # Calculate face distances
            distances = face_recognition.face_distance(known_encodings, unknown_encoding)
            
            # Find the best match (minimum distance)
            best_match_index = np.argmin(distances)
            best_distance = distances[best_match_index]
            
            # Check if the best match is within tolerance
            if best_distance <= tolerance:
                return best_match_index, best_distance
            
            return None, None
            
        except Exception as e:
            logger.error(f"Error in recognize_face_from_list: {e}")
            return None, None
    
    def register_face(self, user_id, user_type, encoding):
        """Register a new face encoding"""
        try:
            key = f"{user_type}_{user_id}"
            self.known_encodings[key] = {
                'encoding': encoding,
                'timestamp': datetime.now(),
                'user_id': user_id,
                'user_type': user_type
            }
            
            # Save to file
            self.save_known_encodings()
            
            # Also save individual file
            np.save(os.path.join(self.encodings_dir, f"{key}.npy"), encoding)
            
            logger.info(f"Registered face for {key}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering face: {e}")
            return False
    
    def recognize_face(self, unknown_encoding, threshold=0.6):
        """
        Recognize a face from known encodings
        Returns: (user_id, user_type, confidence) or (None, None, 0)
        """
        try:
            if unknown_encoding is None:
                return None, None, 0
            
            best_match = None
            best_distance = float('inf')
            
            for key, data in self.known_encodings.items():
                known_encoding = data['encoding']
                distance = np.linalg.norm(known_encoding - unknown_encoding)
                
                if distance < best_distance:
                    best_distance = distance
                    best_match = data
            
            if best_match and best_distance < threshold:
                confidence = 1 - (best_distance / threshold)
                logger.info(f"Recognized: {best_match['user_id']}, Distance: {best_distance:.4f}")
                return best_match['user_id'], best_match['user_type'], confidence
            
            logger.info(f"No match found. Best distance: {best_distance:.4f}")
            return None, None, 0
            
        except Exception as e:
            logger.error(f"Error recognizing face: {e}")
            return None, None, 0
    
    def detect_faces_in_frame(self, frame):
        """Detect all faces in a video frame"""
        try:
            # Resize frame for faster processing
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            
            # Convert BGR to RGB
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # Find face locations
            face_locations = face_recognition.face_locations(rgb_small_frame, model='hog')
            
            # Convert back to original scale
            face_locations = [(top*4, right*4, bottom*4, left*4) 
                             for (top, right, bottom, left) in face_locations]
            
            return face_locations
            
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return []
    
    def draw_face_boxes(self, frame, face_locations, names=None):
        """Draw boxes around detected faces"""
        try:
            for i, (top, right, bottom, left) in enumerate(face_locations):
                # Draw box
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                
                # Draw label
                if names and i < len(names):
                    cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
                    cv2.putText(frame, names[i], (left + 6, bottom - 6), 
                              cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)
                else:
                    cv2.putText(frame, "Face", (left + 6, bottom - 6), 
                              cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 255, 255), 1)
            
            return frame
            
        except Exception as e:
            logger.error(f"Error drawing face boxes: {e}")
            return frame
    
    def get_face_count(self, image):
        """Count number of faces in image"""
        try:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_image, model='hog')
            return len(face_locations)
        except Exception as e:
            logger.error(f"Error counting faces: {e}")
            return 0