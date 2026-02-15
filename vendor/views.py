from django.shortcuts import render, redirect
from account.models import User
from vendor.models import Store, category   

def vendor_dashboard(request):
    user_id = request.session.get('user_id')
    role = request.session.get('role')

    if not user_id:
        return redirect('login')

    if role != 'vendor':
        return redirect('login')

    # 🔹 fetch vendor details
    vendor = User.objects.get(id=user_id)   

    return render(request, 'vendor/dashboard.html', {
        'vendor': vendor
    })


def vendor_store(request):

    vendor_id = request.session.get("user_id")

    if not vendor_id:
        return redirect("login")

    store = Store.objects.filter(vendor_id=vendor_id).first()
    categories = category.objects.all()

    if request.method == "POST":

        store_name = request.POST.get("store_name")
        description = request.POST.get("description")
        category_id = request.POST.get("category")
        address = request.POST.get("address")
        city = request.POST.get("city")
        price_start = request.POST.get("price_start")
        image = request.FILES.get("profile_image")

        category = category.objects.get(id=category_id)

        if store:
            # update
            store.store_name = store_name
            store.description = description
            store.category = category
            store.address = address
            store.city = city
            store.price_start = price_start

            if image:
                store.profile_image = image

            store.save()

        else:
            # create
            Store.objects.create(
                vendor_id=vendor_id,
                store_name=store_name,
                description=description,
                category=category,
                address=address,
                city=city,
                price_start=price_start,
                profile_image=image
            )

        return redirect("vendor_store")

    return render(request, "vendor/store.html", {
        "store": store,
        "categories": categories
    })
