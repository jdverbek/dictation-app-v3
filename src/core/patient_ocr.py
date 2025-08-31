"""
OCR system for extracting patient ID from photos
"""

import cv2
import pytesseract
import re
from datetime import datetime
from typing import Tuple, Optional
import numpy as np
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class PatientIDExtractor:
    """
    Extract patient ID and DOB from wristband/card photos
    """
    
    def __init__(self):
        # Configure Tesseract for Dutch
        self.tesseract_config = '--oem 3 --psm 6 -l nld+eng'
        
    def extract_from_image(self, image_file) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract patient ID and DOB from image
        Returns: (patient_id, date_of_birth)
        """
        try:
            # Read image
            if isinstance(image_file, str):
                image = Image.open(image_file)
            else:
                image = Image.open(image_file)
            
            # Preprocess image for better OCR
            processed_image = self._preprocess_image(image)
            
            # Extract text
            text = pytesseract.image_to_string(
                processed_image, 
                config=self.tesseract_config
            )
            
            logger.info(f"OCR extracted text: {text[:100]}...")
            
            # Extract patient ID and DOB
            patient_id = self._extract_patient_id(text)
            dob = self._extract_date_of_birth(text)
            
            # Validate extracted data
            if patient_id and self._validate_patient_id(patient_id):
                if dob and self._validate_date(dob):
                    return patient_id, dob
            
            # Try alternative extraction methods
            return self._alternative_extraction(image)
            
        except Exception as e:
            logger.error(f"OCR extraction error: {str(e)}")
            return None, None
    
    def _preprocess_image(self, image: Image) -> np.ndarray:
        """Preprocess image for better OCR accuracy"""
        try:
            # Convert to OpenCV format
            img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                gray, 255, 
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(thresh)
            
            # Deskew if needed
            angle = self._get_skew_angle(denoised)
            if abs(angle) > 0.5:
                denoised = self._rotate_image(denoised, angle)
            
            return denoised
        except Exception as e:
            logger.error(f"Image preprocessing error: {str(e)}")
            return np.array(image)
    
    def _get_skew_angle(self, image: np.ndarray) -> float:
        """Calculate skew angle of the image"""
        try:
            # Use HoughLines to detect text lines
            edges = cv2.Canny(image, 50, 150, apertureSize=3)
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is not None:
                angles = []
                for rho, theta in lines[:10]:  # Use first 10 lines
                    angle = np.degrees(theta) - 90
                    angles.append(angle)
                
                # Return median angle
                return np.median(angles) if angles else 0
            
            return 0
        except:
            return 0
    
    def _rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """Rotate image to correct skew"""
        try:
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            
            # Calculate rotation matrix
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            
            # Perform rotation
            rotated = cv2.warpAffine(image, M, (w, h), 
                                   flags=cv2.INTER_CUBIC, 
                                   borderMode=cv2.BORDER_REPLICATE)
            
            return rotated
        except:
            return image
    
    def _extract_patient_id(self, text: str) -> Optional[str]:
        """Extract patient ID from OCR text"""
        # Common patterns for patient IDs
        patterns = [
            r'(?:Patient\s*ID|ID|Patiënt)\s*[:.]?\s*([A-Z0-9]{6,12})',
            r'(?:BSN|Nummer)\s*[:.]?\s*(\d{9})',
            r'(?:MRN|Medical\s*Record)\s*[:.]?\s*([A-Z0-9]{6,12})',
            r'\b([A-Z]{2}\d{6,10})\b',  # Generic pattern
            r'(?:Ziekenhuis\s*nummer|ZH\s*nr)\s*[:.]?\s*([A-Z0-9]{6,12})',
            r'(?:Patiëntnummer|Pat\s*nr)\s*[:.]?\s*([A-Z0-9]{6,12})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted_id = match.group(1).upper()
                logger.info(f"Extracted patient ID: {extracted_id}")
                return extracted_id
        
        # Try to find any alphanumeric sequence that looks like an ID
        alphanumeric_matches = re.findall(r'\b[A-Z0-9]{6,12}\b', text.upper())
        if alphanumeric_matches:
            logger.info(f"Found potential patient ID: {alphanumeric_matches[0]}")
            return alphanumeric_matches[0]
        
        return None
    
    def _extract_date_of_birth(self, text: str) -> Optional[str]:
        """Extract date of birth from OCR text"""
        # Date patterns
        patterns = [
            r'(?:Geboren|Geb|DOB|Date\s*of\s*Birth)\s*[:.]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
            r'(?:Geboren|Geb|DOB)\s*[:.]?\s*(\d{1,2}\s+\w+\s+\d{4})',
            r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b',
            r'(?:Geboortedatum|Gebdat)\s*[:.]?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                # Normalize to dd/mm/yyyy format
                normalized_date = self._normalize_date(date_str)
                if normalized_date:
                    logger.info(f"Extracted DOB: {normalized_date}")
                    return normalized_date
        
        return None
    
    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Normalize date to dd/mm/yyyy format"""
        # Try different date formats
        formats = [
            '%d/%m/%Y', '%d-%m-%Y', '%d %B %Y', 
            '%d %b %Y', '%d/%m/%y', '%d-%m-%y',
            '%d.%m.%Y', '%d.%m.%y'
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                # Convert 2-digit years to 4-digit
                if dt.year < 50:
                    dt = dt.replace(year=dt.year + 2000)
                elif dt.year < 100:
                    dt = dt.replace(year=dt.year + 1900)
                
                return dt.strftime('%d/%m/%Y')
            except:
                continue
        
        return None
    
    def _validate_patient_id(self, patient_id: str) -> bool:
        """Validate patient ID format"""
        if not patient_id:
            return False
            
        # Basic validation rules
        if len(patient_id) < 6 or len(patient_id) > 12:
            return False
        
        # Must contain at least some numbers
        if not any(c.isdigit() for c in patient_id):
            return False
        
        # Check for obvious OCR errors
        if patient_id.count('O') > len(patient_id) // 2:  # Too many O's (likely 0's)
            return False
        
        return True
    
    def _validate_date(self, date_str: str) -> bool:
        """Validate date format and reasonableness"""
        try:
            dt = datetime.strptime(date_str, '%d/%m/%Y')
            # Check if date is reasonable (not in future, not too old)
            now = datetime.now()
            age = (now - dt).days / 365.25
            return 0 <= age <= 120
        except:
            return False
    
    def _alternative_extraction(self, image: Image) -> Tuple[Optional[str], Optional[str]]:
        """Try alternative extraction methods"""
        try:
            # Try different OCR configurations
            configs = [
                '--oem 3 --psm 7 -l nld+eng',  # Single text line
                '--oem 3 --psm 8 -l nld+eng',  # Single word
                '--oem 3 --psm 13 -l nld+eng'  # Raw line
            ]
            
            for config in configs:
                text = pytesseract.image_to_string(image, config=config)
                patient_id = self._extract_patient_id(text)
                dob = self._extract_date_of_birth(text)
                
                if patient_id and self._validate_patient_id(patient_id):
                    if dob and self._validate_date(dob):
                        return patient_id, dob
            
            # If still no success, try with image enhancement
            enhanced_image = self._enhance_image(image)
            text = pytesseract.image_to_string(enhanced_image, config=self.tesseract_config)
            
            patient_id = self._extract_patient_id(text)
            dob = self._extract_date_of_birth(text)
            
            return patient_id, dob
            
        except Exception as e:
            logger.error(f"Alternative extraction error: {str(e)}")
            return None, None
    
    def _enhance_image(self, image: Image) -> Image:
        """Enhance image for better OCR"""
        try:
            # Convert to numpy array
            img_array = np.array(image)
            
            # Increase contrast
            img_array = cv2.convertScaleAbs(img_array, alpha=1.5, beta=0)
            
            # Apply Gaussian blur to reduce noise
            img_array = cv2.GaussianBlur(img_array, (3, 3), 0)
            
            # Convert back to PIL Image
            return Image.fromarray(img_array)
        except:
            return image

