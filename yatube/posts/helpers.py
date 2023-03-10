from django.core.paginator import Paginator


def pagin(request, *args, **kwargs):
    paginator = Paginator(*args, **kwargs)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
