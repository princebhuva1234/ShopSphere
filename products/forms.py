from django import forms

from .models import Product


# =========================================================
# SELLER PRODUCT FORM
# =========================================================

class ProductForm(forms.ModelForm):

    class Meta:

        model = Product

        fields = [
            'category',
            'name',
            'description',
            'brand',
            'price',
            'discount_price',
            'stock_quantity',
            'is_active',
        ]

        widgets = {

            'category': forms.Select(
                attrs={
                    'class': 'form-control',
                }
            ),

            'name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter product name',
                }
            ),

            'description': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Describe your product',
                    'rows': 5,
                }
            ),

            'brand': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter brand name',
                }
            ),

            'price': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Regular price',
                    'min': '0.01',
                    'step': '0.01',
                }
            ),

            'discount_price': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Discounted price (optional)',
                    'min': '0.01',
                    'step': '0.01',
                }
            ),

            'stock_quantity': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Available stock',
                    'min': '0',
                    'step': '1',
                }
            ),

            'is_active': forms.CheckboxInput(
                attrs={
                    'class': 'form-checkbox',
                }
            ),

        }

    # -----------------------------------------------------
    # VALIDATE PRICE AND DISCOUNT
    # -----------------------------------------------------

    def clean(self):

        cleaned_data = super().clean()

        price = cleaned_data.get('price')
        discount_price = cleaned_data.get('discount_price')
        stock_quantity = cleaned_data.get('stock_quantity')

        if price is not None and price <= 0:

            self.add_error(
                'price',
                'Product price must be greater than zero.'
            )

        if discount_price is not None:

            if discount_price <= 0:

                self.add_error(
                    'discount_price',
                    'Discounted price must be greater than zero.'
                )

            elif price is not None and discount_price >= price:

                self.add_error(
                    'discount_price',
                    'Discounted price must be lower than regular price.'
                )

        if stock_quantity is not None and stock_quantity < 0:

            self.add_error(
                'stock_quantity',
                'Stock quantity cannot be negative.'
            )

        return cleaned_data