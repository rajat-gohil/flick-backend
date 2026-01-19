from rest_framework.pagination import PageNumberPagination

class SwipeHistoryPagination(PageNumberPagination):
    page_size = 10                 # swipes per page
    page_size_query_param = "size" # ?size=20
    max_page_size = 50
