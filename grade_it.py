import cv2
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import math
import json
import os

def grade_with_precise_positions(binary_img, bubble_positions, expected_answers, threshold, debug=False):
    """
    Grade using precisely KNOWN bubble positions
    """
    question_results = []
    score = 0
    
    debug_img = cv2.cvtColor(binary_img, cv2.COLOR_GRAY2BGR) if debug else None
    
    for q_data in bubble_positions:
        q_num = q_data['question']
        bubbles = q_data['bubbles']
        
        bubble_status = {}
        marked_choices = []
        
        for bubble in bubbles:
            choice = bubble['choice']
            x1, y1, x2, y2 = bubble['bbox']
            
            # Extracting the bubble region
            bubble_roi = binary_img[max(0,y1):min(binary_img.shape[0],y2), 
                                  max(0,x1):min(binary_img.shape[1],x2)]
            
            if bubble_roi.size == 0:
                filled_ratio = 0
            else:
                total_pixels = bubble_roi.size
                filled_pixels = np.sum(bubble_roi > 0)
                filled_ratio = filled_pixels / total_pixels
            
            bubble_status[choice] = filled_ratio
            
            if filled_ratio > threshold:
                marked_choices.append(choice)
        
        # Determining answer
        if len(marked_choices) == 1:
            student_answer = marked_choices[0]
            is_correct = (student_answer == expected_answers[q_num-1])
            if is_correct:
                score += 1
        else:
            student_answer = "MULTI" if len(marked_choices) > 1 else "NONE"
            is_correct = False
        
        question_results.append({
            'question': q_num,
            'student_answer': student_answer,
            'correct_answer': expected_answers[q_num-1],
            'is_correct': is_correct,
            'bubble_status': bubble_status
        })
        
        # Debug mode
        if debug and debug_img is not None:
            correct_answer = expected_answers[q_num-1]
            
            for bubble in bubbles:
                choice = bubble['choice']
                center_x, center_y = bubble['center']
                filled_ratio = bubble_status[choice]
                
                # Determine colors based on answer status
                if choice == correct_answer and choice == student_answer:
                    color = (0, 255, 0)  # Green
                    status_text = "CORRECT"
                elif choice == correct_answer and student_answer not in ['MULTI', 'NONE']:
                    color = (255, 0, 0)  # Blue
                    status_text = "SHOULD BE"
                elif choice == student_answer and not is_correct and student_answer not in ['MULTI', 'NONE']:
                    color = (0, 0, 255)  # Red
                    status_text = "WRONG"
                elif filled_ratio > threshold:
                    color = (0, 165, 255)  # Orange
                    status_text = "MULTI"
                else:
                    color = (128, 128, 128)  # Gray
                    status_text = "empty"
                
                cv2.circle(debug_img, (center_x, center_y), 20, color, 3)
                
                cv2.putText(debug_img, f"{filled_ratio:.2f}", 
                           (center_x-25, center_y-25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                cv2.putText(debug_img, status_text, 
                           (center_x-25, center_y+35), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            # Summary
            question_pos = q_data.get('question_pos', (bubbles[0]['center'][0] - 100, bubbles[0]['center'][1]))
            summary_color = (0, 255, 0) if is_correct else (0, 0, 255)
            summary_text = f"Q{q_num}: Student={student_answer}, Correct={correct_answer} ({'✓' if is_correct else '✗'})"
            cv2.putText(debug_img, summary_text, 
                       (int(question_pos[0]), int(question_pos[1]) - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, summary_color, 2)
    
    if debug and debug_img is not None:
        print("Grading visualization:")
        print("- GREEN: Correctly marked answer")
        print("- BLUE: Correct answer (should have been marked)")
        print("- RED: Wrong answer marked by student") 
        print("- ORANGE: Multiple answers marked")
        print("- GRAY: Unmarked bubble")
        
        cv2.imshow("Grading Results", debug_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return {
        'total_score': score,
        'max_score': len(bubble_positions),
        'percentage': (score / len(bubble_positions)) * 100,
        'question_results': question_results,
        'multiple_answers': len([r for r in question_results if r['student_answer'] == 'MULTI']),
        'unanswered': len([r for r in question_results if r['student_answer'] == 'NONE'])
    }

def grade_gabarito_improved(
    image_path,
    expected_answers,
    position_data=None,
    choices=("A", "B", "C", "D", "E"),
    threshold=0.2,
    debug=False
):
    """
    Grade improved answer sheets with header labels
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not load image from {image_path}")
    
    # Preprocess
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Enhanced preprocessing
    kernel = np.ones((3,3), np.uint8)
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 10
    )
    
    # Removing small noise
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    
    if debug:
        print("Preprocessed binary image:")
        cv2.imshow("Binary Image", binary)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    if position_data is None:
        print("Warning: No position data provided. You need to generate position data first.")
        return None
    
    bubble_positions = position_data['bubble_positions']
    
    return grade_with_precise_positions(binary, bubble_positions, expected_answers, threshold, debug)

def print_grade_report(grade_results):
    """Print a formatted grade report"""
    results = grade_results
    print(f"\n=== GRADE REPORT ===")
    print(f"Score: {results['total_score']}/{results['max_score']}")
    print(f"Percentage: {results['percentage']:.1f}%")
    print(f"Multiple answers: {results['multiple_answers']}")
    print(f"Unanswered: {results['unanswered']}")
    
    # Calculate accuracy for answered questions
    answered_questions = len(results['question_results']) - results['unanswered'] - results['multiple_answers']
    if answered_questions > 0:
        accuracy = (results['total_score'] / answered_questions) * 100
        print(f"Accuracy (answered questions): {accuracy:.1f}%")
    
    print(f"\n=== DETAILED RESULTS ===")
    for item in results['question_results']:
        status = "○" if item['is_correct'] else "X"
        if item['student_answer'] in ['MULTI', 'NONE']:
            status = "!"  # Special status for multiple or no answers
        
        print(f"Q{item['question']:02d}: {status} Student={item['student_answer']:5} Correct={item['correct_answer']} ", end="")
        
        # Showing bubble status for incorrect answers
        if not item['is_correct'] and item['student_answer'] not in ['MULTI', 'NONE']:
            marked_ratio = item['bubble_status'][item['student_answer']]
            correct_ratio = item['bubble_status'][item['correct_answer']]
            print(f"(marked: {marked_ratio:.2f}, correct: {correct_ratio:.2f})", end="")
        print()
    
    print(f"\n=== INCORRECT ANSWERS ===")
    incorrect = [r for r in results['question_results'] if not r['is_correct']]
    if incorrect:
        for item in incorrect:
            if item['student_answer'] == 'MULTI':
                marked = [ch for ch, ratio in item['bubble_status'].items() if ratio > 0.4]
                print(f"Q{item['question']:02d}: MULTIPLE answers {marked}, Correct={item['correct_answer']}")
            elif item['student_answer'] == 'NONE':
                print(f"Q{item['question']:02d}: UNANSWERED, Correct={item['correct_answer']}")
            else:
                print(f"Q{item['question']:02d}: Student={item['student_answer']}, Correct={item['correct_answer']}")
    else:
        print("No incorrect answers!")

if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')

    marked_path = "./templates/marked_demo.png"
    position_file = "./templates/gabarito_demo_positions.json"

    print(f"Using marked sample: {marked_path}")
    
    # Load position data
    with open(position_file, 'r') as f:
        position_data = json.load(f)
    
    expected_answers = ["A", "B", "D", "E", "E", "E", "D", "B", "A", "A", 
                       "C", "C", "C", "D", "E", "A", "E", "B", "A", "E",
                       "B", "B", "C", "B", "E"]
    
    results = grade_gabarito_improved(
        image_path=marked_path,
        expected_answers=expected_answers,
        position_data=position_data,
        debug=True
    )
    
    print_grade_report(results)