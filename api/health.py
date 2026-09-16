def handler(request):
    return (
        200,
        {"Content-Type": "application/json", "Cache-Control": "no-store"},
        '{"status":"ok","buildId":"dev","engineVersion":"1.0.0","paidFeaturesEnabled":false}',
    )
