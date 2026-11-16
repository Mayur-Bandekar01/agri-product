// Modal Diagnostic Script
// Copy and paste this into the browser console (F12 -> Console tab)

console.log('=== MODAL DIAGNOSTIC STARTED ===');

// Test 1: Check if modal HTML exists
console.log('\n[Test 1] Checking if modal HTML exists...');
const modal = document.getElementById('entityModal');
if (modal) {
    console.log('✅ Modal HTML found:', modal);
    console.log('   - Current classes:', modal.className);
    console.log('   - Current display:', window.getComputedStyle(modal).display);
} else {
    console.error('❌ Modal HTML NOT FOUND - id="entityModal" does not exist!');
}

// Test 2: Check if modal has CSS applied
console.log('\n[Test 2] Checking modal CSS...');
if (modal) {
    const styles = window.getComputedStyle(modal);
    console.log('   - position:', styles.position, '(should be "fixed")');
    console.log('   - display:', styles.display, '(should be "none" or "flex")');
    console.log('   - z-index:', styles.zIndex, '(should be "10000")');
    console.log('   - background:', styles.background);
    
    if (styles.position === 'fixed') {
        console.log('✅ Modal CSS is loaded correctly');
    } else {
        console.error('❌ Modal CSS NOT loaded - position is not fixed!');
        console.log('   This means the CSS file was not loaded or cached old version');
    }
}

// Test 3: Check if openFarmerForm function exists
console.log('\n[Test 3] Checking if openFarmerForm function exists...');
if (typeof openFarmerForm === 'function') {
    console.log('✅ openFarmerForm function exists');
} else {
    console.error('❌ openFarmerForm function NOT FOUND!');
}

// Test 4: Check if buildFarmerForm function exists
console.log('\n[Test 4] Checking if buildFarmerForm function exists...');
if (typeof buildFarmerForm === 'function') {
    console.log('✅ buildFarmerForm function exists');
} else {
    console.error('❌ buildFarmerForm function NOT FOUND!');
}

// Test 5: Check if farmers array exists
console.log('\n[Test 5] Checking farmers data...');
if (typeof farmers !== 'undefined') {
    console.log('✅ farmers array exists, length:', farmers.length);
} else {
    console.error('❌ farmers array NOT FOUND!');
}

// Test 6: Try to manually open the modal
console.log('\n[Test 6] Attempting to manually open modal...');
if (modal) {
    try {
        modal.classList.add('open');
        console.log('✅ Added "open" class to modal');
        console.log('   - New classes:', modal.className);
        console.log('   - New display:', window.getComputedStyle(modal).display);
        
        if (window.getComputedStyle(modal).display === 'flex') {
            console.log('✅ Modal is now visible!');
        } else {
            console.error('❌ Modal still not visible - CSS might not be working');
        }
    } catch (e) {
        console.error('❌ Error opening modal:', e);
    }
}

// Test 7: Check CSS file loaded
console.log('\n[Test 7] Checking if CSS file is loaded...');
const styleSheets = Array.from(document.styleSheets);
const styleCSS = styleSheets.find(sheet => sheet.href && sheet.href.includes('style.css'));
if (styleCSS) {
    console.log('✅ style.css is loaded:', styleCSS.href);
    console.log('   - CSS file version:', styleCSS.href.split('?v=')[1] || 'no version');
} else {
    console.error('❌ style.css NOT FOUND in loaded stylesheets!');
}

// Test 8: Test the actual openFarmerForm function
console.log('\n[Test 8] Testing openFarmerForm() function...');
console.log('Run this command manually: openFarmerForm()');
console.log('Or click the button in the UI');

console.log('\n=== DIAGNOSTIC COMPLETE ===');
console.log('\nTo test manually, run: openFarmerForm()');
