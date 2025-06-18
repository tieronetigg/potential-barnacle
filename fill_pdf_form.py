#!/usr/bin/env python3
"""
PDF Form Filler Script

This script reads JSON data and fills PDF form fields (annotations) with proper
multiline handling and specified line spacing.

Requirements:
- PyMuPDF (fitz): pip install PyMuPDF
- json (built-in)
"""

import json
import fitz  # PyMuPDF
import sys
import os
from typing import Dict, List, Tuple, Any


class PDFFormFiller:
    def __init__(self, pdf_path: str, json_path: str, output_path: str = None):
        """
        Initialize the PDF form filler.
        
        Args:
            pdf_path: Path to the input PDF file
            json_path: Path to the JSON data file
            output_path: Path for the output PDF (defaults to adding '_filled' suffix)
        """
        self.pdf_path = pdf_path
        self.json_path = json_path
        self.output_path = output_path or self._generate_output_path()
        self.line_spacing_multiplier = 2.20
        self.max_lines_per_field = None  # Set to a number to limit lines per field (e.g., 5)
        self.field_specific_line_limits = {}  # Field-specific line limits
        
        # Track overflow text for each field
        self.field_overflow_data = {}  # Stores overflow info for each field
        
        # Load JSON data
        self.data = self._load_json_data()
        
        # Open PDF document
        self.doc = fitz.open(pdf_path)
        
    def _generate_output_path(self) -> str:
        """Generate output path by adding '_filled' suffix to input PDF."""
        base, ext = os.path.splitext(self.pdf_path)
        return f"{base}_filled{ext}"
        
    def _load_json_data(self) -> Dict[str, Any]:
        """Load and return JSON data from file."""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"JSON file not found: {self.json_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
            
    def set_max_lines_per_field(self, max_lines: int):
        """
        Set the maximum number of lines for all multiline fields.
        
        Args:
            max_lines: Maximum number of lines to display in each field
        """
        self.max_lines_per_field = max_lines
        
    def set_field_line_limit(self, field_name: str, max_lines: int):
        """
        Set a specific line limit for a particular field.
        
        Args:
            field_name: Name of the field (e.g., "N5text[0]")
            max_lines: Maximum number of lines for this specific field
        """
        self.field_specific_line_limits[field_name] = max_lines
        
    def set_multiple_field_limits(self, field_limits: Dict[str, int]):
        """
        Set line limits for multiple fields at once.
        
        Args:
            field_limits: Dictionary of field_name -> max_lines
                         e.g., {"N5text[0]": 3, "N6text[0]": 5}
        """
        self.field_specific_line_limits.update(field_limits)
        
    def get_field_full_line_count(self, field_name: str, text: str, available_width: float, font_size: float = 11) -> int:
        """
        Calculate how many lines a field would need without any limits.
        
        Args:
            field_name: Name of the field
            text: Text content to measure
            available_width: Available width for the field
            font_size: Font size (default 11)
            
        Returns:
            Total number of lines needed for the full text
        """
        if not text:
            return 0
            
        lines = self._split_text_to_lines(str(text), available_width, font_size)
        return len(lines)
        
    def get_field_overflow_text(self, field_name: str) -> str:
        """
        Get the overflow text that was truncated from a specific field.
        
        Args:
            field_name: Name of the field
            
        Returns:
            The text that was truncated, or empty string if no overflow
        """
        if field_name in self.field_overflow_data:
            overflow_lines = self.field_overflow_data[field_name].get('overflow_lines', [])
            return ' '.join(overflow_lines)
        return ""
        
    def get_all_overflow_text(self, separator: str = "\n\n") -> str:
        """
        Get all overflow text from all fields combined.
        
        Args:
            separator: Text to use between different field overflows
            
        Returns:
            Combined overflow text from all fields
        """
        overflow_parts = []
        
        for field_name, overflow_info in self.field_overflow_data.items():
            overflow_lines = overflow_info.get('overflow_lines', [])
            if overflow_lines:
                field_overflow = ' '.join(overflow_lines)
                # Add field context
                overflow_parts.append(f"[{field_name}]: {field_overflow}")
                
        return separator.join(overflow_parts)
        
    def get_overflow_summary(self) -> Dict[str, Dict]:
        """
        Get detailed overflow information for all fields.
        
        Returns:
            Dictionary with field names as keys and overflow info as values
        """
        summary = {}
        
        for field_name, overflow_info in self.field_overflow_data.items():
            summary[field_name] = {
                'total_lines': overflow_info.get('total_lines', 0),
                'displayed_lines': overflow_info.get('displayed_lines', 0),
                'overflow_lines': len(overflow_info.get('overflow_lines', [])),
                'overflow_text': ' '.join(overflow_info.get('overflow_lines', []))
            }
            
        return summary
        
    def _calculate_line_spacing(self, font_size: float) -> float:
        """Calculate line spacing based on font size and multiplier."""
        return font_size * self.line_spacing_multiplier
        
    def _get_text_width(self, text: str, font_size: float, font_name: str = "helv") -> float:
        """
        Get the actual width of text using PyMuPDF's text measurement.
        
        Args:
            text: The text to measure
            font_size: Font size for measurement
            font_name: Font name for measurement
            
        Returns:
            Width of the text in points
        """
        try:
            # Use a more accurate approximation that matches real text width better
            # Helvetica at 11pt averages about 0.45-0.5 width per character
            return len(text) * font_size * 0.45  # More aggressive/accurate approximation
        except:
            # Even more conservative fallback
            return len(text) * font_size * 0.5
        
    def _split_text_to_lines(self, text: str, max_width: float, font_size: float, 
                            font_name: str = "helv") -> List[str]:
        """
        Split text into lines with intelligent word wrapping that flows naturally.
        
        Args:
            text: The text to split
            max_width: Maximum width for each line
            font_size: Font size for text measurement
            font_name: Font name for text measurement
            
        Returns:
            List of text lines that fit within max_width
        """
        if not text:
            return [""]
            
        # Use full width for maximum text flow
        effective_width = max_width  # Use the complete available width
        
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            # Test if adding this word would exceed the width
            test_line = current_line + (" " if current_line else "") + word
            test_width = self._get_text_width(test_line, font_size, font_name)
            
            if test_width <= effective_width:
                # Word fits, add it to current line
                current_line = test_line
            else:
                # Word doesn't fit
                if current_line:
                    # Save current line and start new line with this word
                    lines.append(current_line)
                    current_line = word
                    
                    # Check if the single word is too long for a line
                    if self._get_text_width(word, font_size, font_name) > effective_width:
                        # Break long word into smaller parts
                        char_lines = self._break_long_word(word, effective_width, font_size, font_name)
                        lines.extend(char_lines[:-1])  # Add all but the last part
                        current_line = char_lines[-1] if char_lines else ""  # Keep last part for next iteration
                else:
                    # Even single word doesn't fit, break it
                    char_lines = self._break_long_word(word, effective_width, font_size, font_name)
                    lines.extend(char_lines[:-1])
                    current_line = char_lines[-1] if char_lines else ""
        
        # Add the last line if it has content
        if current_line:
            lines.append(current_line)
            
        return lines if lines else [""]
        
    def _break_long_word(self, word: str, max_width: float, font_size: float, font_name: str) -> List[str]:
        """
        Break a long word that doesn't fit on a single line.
        
        Args:
            word: The word to break
            max_width: Maximum width for each line segment
            font_size: Font size for measurement
            font_name: Font name for measurement
            
        Returns:
            List of word segments that fit within max_width
        """
        if not word:
            return [""]
            
        segments = []
        current_segment = ""
        
        for char in word:
            test_segment = current_segment + char
            if self._get_text_width(test_segment, font_size, font_name) <= max_width:
                current_segment = test_segment
            else:
                if current_segment:
                    segments.append(current_segment)
                    current_segment = char
                else:
                    # Even single character is too wide, just add it anyway
                    segments.append(char)
                    current_segment = ""
        
        if current_segment:
            segments.append(current_segment)
            
        return segments if segments else [word]
        
    def _fill_text_field(self, page: fitz.Page, field: Dict, text: str):
        """
        Fill a text field with proper multiline handling and top padding.
        
        Args:
            page: The PDF page containing the field
            field: Field dictionary containing position and properties
            text: Text content to fill
        """
        if not text:
            return
            
        # Get field rectangle
        rect = field.get("rect")
        if not rect:
            print(f"Warning: No rectangle found for field")
            return
            
        field_rect = fitz.Rect(rect)
        field_name = field.get("field_name", "")
        
        # Fixed font size as requested
        font_size = 11
            
        # Calculate available width and height with minimal margins
        left_margin = 1   # Minimal left margin
        right_margin = 0  # No right margin to use full width
        top_padding = 6   # Top padding as requested
        bottom_margin = 2
        
        available_width = field_rect.width - left_margin - right_margin
        available_height = field_rect.height - top_padding - bottom_margin
        
        # Split text into lines using intelligent word wrapping
        all_lines = self._split_text_to_lines(str(text), available_width, font_size)
        total_lines_needed = len(all_lines)
        
        # Apply line limits (field-specific takes priority over global)
        max_lines = None
        if field_name in self.field_specific_line_limits:
            max_lines = self.field_specific_line_limits[field_name]
            print(f"Using field-specific limit of {max_lines} lines for '{field_name}'")
        elif self.max_lines_per_field is not None:
            max_lines = self.max_lines_per_field
            print(f"Using global limit of {max_lines} lines")
            
        # Determine which lines to display and which overflow
        if max_lines is not None and len(all_lines) > max_lines:
            lines = all_lines[:max_lines]  # Lines to display
            overflow_lines = all_lines[max_lines:]  # Lines that overflow
            
            # Store overflow information
            self.field_overflow_data[field_name] = {
                'total_lines': total_lines_needed,
                'displayed_lines': len(lines),
                'overflow_lines': overflow_lines,
                'original_text': str(text)
            }
            
            print(f"Text truncated to {max_lines} lines for field '{field_name}' (total needed: {total_lines_needed})")
        else:
            lines = all_lines  # No truncation needed
            
            # Still track info even if no overflow
            self.field_overflow_data[field_name] = {
                'total_lines': total_lines_needed,
                'displayed_lines': len(lines),
                'overflow_lines': [],
                'original_text': str(text)
            }
        
        # Calculate line spacing - fixed at 2.20x
        line_spacing = self._calculate_line_spacing(font_size)
        
        # No font size adjustment - keep at 11pt as requested
        # If text doesn't fit, we'll just let it overflow or truncate
        
        # Position text from top-left with padding
        start_x = field_rect.x0 + left_margin
        start_y = field_rect.y0 + top_padding + font_size  # Start from top with padding and font size offset
        
        # Add each line of text
        for i, line in enumerate(lines):
            y_position = start_y + (i * line_spacing)
            
            # Stop if we've exceeded the field height
            if y_position > field_rect.y1 - bottom_margin:
                print(f"Warning: Text truncated - not all lines fit in field (keeping font size 11)")
                break
                
            # Insert text
            try:
                page.insert_text(
                    point=(start_x, y_position),
                    text=line,
                    fontsize=font_size,
                    color=(0, 0, 0),  # Black color
                    fontname="helv"  # Helvetica
                )
            except Exception as e:
                print(f"Error inserting text '{line}': {e}")
                
    def _fill_checkbox_field(self, page: fitz.Page, field: Dict, value: str):
        """
        Fill a checkbox field.
        
        Args:
            page: The PDF page containing the field
            field: Field dictionary containing position and properties
            value: Value to determine if checkbox should be checked
        """
        if not value or value.lower() not in ['yes', 'true', '1', 'on', 'checked']:
            return
            
        rect = field.get("rect")
        if not rect:
            return
            
        field_rect = fitz.Rect(rect)
        
        # Draw checkmark or X
        # Create a simple checkmark using drawing commands
        try:
            # Draw an X or checkmark
            page.draw_line(
                p1=(field_rect.x0 + 2, field_rect.y0 + 2),
                p2=(field_rect.x1 - 2, field_rect.y1 - 2),
                color=(0, 0, 0),
                width=2
            )
            page.draw_line(
                p1=(field_rect.x1 - 2, field_rect.y0 + 2),
                p2=(field_rect.x0 + 2, field_rect.y1 - 2),
                color=(0, 0, 0),
                width=2
            )
        except Exception as e:
            print(f"Error drawing checkbox: {e}")
            
    def get_form_fields(self) -> List[Dict]:
        """
        Extract all form fields from the PDF.
        
        Returns:
            List of dictionaries containing field information
        """
        fields = []
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            
            # Get form fields (annotations)
            for widget in page.widgets():
                field_info = {
                    "page": page_num,
                    "field_name": widget.field_name,
                    "field_type": widget.field_type,
                    "rect": widget.rect,
                    "field_value": widget.field_value,
                    "widget": widget
                }
                fields.append(field_info)
                
        return fields
        
    def fill_form(self):
        """Main method to fill the form with JSON data."""
        print(f"Loading PDF: {self.pdf_path}")
        print(f"Loading JSON data: {self.json_path}")
        
        # Get all form fields
        form_fields = self.get_form_fields()
        
        print(f"Found {len(form_fields)} form fields")
        
        if not form_fields:
            print("No form fields found in PDF. Looking for annotations...")
            # Try to get annotations if no form fields found
            self._fill_using_annotations()
            return
            
        # Process each form field
        filled_count = 0
        
        for field in form_fields:
            field_name = field["field_name"]
            page_num = field["page"]
            page = self.doc[page_num]
            
            # Look for matching data in JSON
            json_value = self.data.get(field_name)
            
            if json_value is not None:
                print(f"Filling field '{field_name}' with data")
                
                field_type = field["field_type"]
                
                if field_type in [fitz.PDF_WIDGET_TYPE_TEXT, fitz.PDF_WIDGET_TYPE_LISTBOX]:
                    self._fill_text_field(page, field, str(json_value))
                elif field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
                    self._fill_checkbox_field(page, field, str(json_value))
                else:
                    # Try to fill as text field for other types
                    self._fill_text_field(page, field, str(json_value))
                
                filled_count += 1
            else:
                print(f"No data found for field '{field_name}'")
                
        print(f"Filled {filled_count} fields")
        
    def _fill_using_annotations(self):
        """Alternative method to fill using annotations if form fields are not found."""
        print("Attempting to fill using annotations...")
        
        filled_count = 0
        
        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            
            # Get all annotations
            annotations = page.annots()
            
            for annot in annotations:
                annot_dict = annot.info
                annot_content = annot_dict.get("content", "")
                annot_rect = annot.rect
                
                # Try to match annotation with JSON data
                for json_key, json_value in self.data.items():
                    if json_value and (json_key.lower() in annot_content.lower() or 
                                     annot_content.lower() in json_key.lower()):
                        
                        print(f"Filling annotation '{annot_content}' with '{json_key}' data")
                        
                        # Create a pseudo-field for the annotation
                        pseudo_field = {
                            "rect": annot_rect,
                            "field_name": json_key,
                            "field_type": "text"
                        }
                        
                        self._fill_text_field(page, pseudo_field, str(json_value))
                        filled_count += 1
                        break
                        
        print(f"Filled {filled_count} annotations")
        
    def save(self):
        """Save the filled PDF to the output path."""
        try:
            self.doc.save(self.output_path)
            print(f"Filled PDF saved to: {self.output_path}")
        except Exception as e:
            print(f"Error saving PDF: {e}")
            raise
            
    def close(self):
        """Close the PDF document."""
        if hasattr(self, 'doc'):
            self.doc.close()
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    """Main function to run the PDF form filler."""
    if len(sys.argv) < 3:
        print("Usage: python fill_pdf_form.py <pdf_file> <json_file> [output_file]")
        print("Example: python fill_pdf_form.py form.pdf data.json filled_form.pdf")
        sys.exit(1)
        
    pdf_file = sys.argv[1]
    json_file = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Validate input files
    if not os.path.exists(pdf_file):
        print(f"Error: PDF file not found: {pdf_file}")
        sys.exit(1)
        
    if not os.path.exists(json_file):
        print(f"Error: JSON file not found: {json_file}")
        sys.exit(1)
        
    try:
        # Fill the form
        with PDFFormFiller(pdf_file, json_file, output_file) as filler:
            filler.fill_form()
            filler.save()
            
        print("PDF form filling completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
