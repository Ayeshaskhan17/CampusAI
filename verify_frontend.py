with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

s_open = content.count('<script')
s_close = content.count('</script>')
print(f'Script tags: <script>: {s_open}, </script>: {s_close}')
assert s_open == s_close, 'Mismatched script tags!'

funcs = ['manageRows', 'confirmDeleteNotice', 'executeDeleteNotice', 'editPage', 'updateNotice', 'refreshNoticesUI']
for fn in funcs:
    found = ('function ' + fn) in content
    print(f'Checking {fn}: {found}')

print('routeNames has edit:', 'edit:"Edit Notice"' in content)
print('facultyRoutes/adminRoutes has edit:', '"edit"' in content)
print('renderApp has edit:', 'route === "edit"' in content)
print('All static checks passed!')
