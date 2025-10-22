
# ============================================
# FILE: sales/views.py
# ============================================
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .agent import query_sales

def query_view(request):
    """Render the query interface"""
    return render(request, 'query.html')

@csrf_exempt
def process_query(request):
    """Process the natural language query"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            question = data.get('question', '')
            
            if not question:
                return JsonResponse({
                    'error': 'No question provided'
                }, status=400)
            
            # Process with LangGraph agent
            result = query_sales(question)
            
            return JsonResponse({
                'success': True,
                'answer': result['answer'],
                'sql_query': result['sql_query'],
                'raw_results': result['raw_results']
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'error': 'Only POST requests allowed'
    }, status=405)
